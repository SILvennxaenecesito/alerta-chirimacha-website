/**
 * Alerta Chirimacha: district totals for the website, straight from the
 * report log (Google Sheet "Denuncias Alerta Chirimacha", tab DENUNCIAS).
 *
 * The website asks this script for numbers each time someone opens the map,
 * so new rows in the sheet show up on the site within about 10 minutes.
 *
 * PRIVACY: this script only ever returns totals per district and year. It
 * never returns names, phone numbers, addresses, household codes (UNICODE),
 * photo links or individual rows. Do not change doGet to return raw values.
 *
 * Setup: see tools/apps-script/README.md (about 5 minutes, once).
 * The same rules are in tools/aggregate_reports.py; keep both in step.
 */

var SHEET_NAME = 'DENUNCIAS';
var CACHE_SECONDS = 600;          // recompute at most every 10 minutes
var CACHE_KEY = 'alerta-chirimacha-totals-v1';

var DISTRICTS = ['Arequipa', 'Alto Selva Alegre', 'Cayma', 'Cerro Colorado', 'Characato', 'Chiguata',
  'Jacobo Hunter', 'La Joya', 'Mariano Melgar', 'Miraflores', 'Mollebaya', 'Paucarpata', 'Pocsi', 'Polobaya',
  'Quequeña', 'Sabandía', 'Sachaca', 'San Juan de Siguas', 'San Juan de Tarucani', 'Santa Isabel de Siguas',
  'Santa Rita de Siguas', 'Socabaya', 'Tiabaya', 'Uchumayo', 'Vítor', 'Yanahuara', 'Yarabamba', 'Yura',
  'José Luis Bustamante y Rivero'];
// Spellings found in the log -> district name used on the site
var ALIASES = {
  'CERCADO': 'Arequipa', 'CERCADO DE AREQUIPA': 'Arequipa', 'ASA': 'Alto Selva Alegre',
  'HUNTER': 'Jacobo Hunter', 'J HUNTER': 'Jacobo Hunter',
  'JOSE NUIS BUSTAMANTE Y RIVERO': 'José Luis Bustamante y Rivero', 'BUSTAMANTE Y RIVERO': 'José Luis Bustamante y Rivero',
  'JLBYR': 'José Luis Bustamante y Rivero', 'J L B Y RIVERO': 'José Luis Bustamante y Rivero'
};
// Outside Arequipa province even when PROVINCIA says AREQUIPA (e.g. El Pedregal is in Majes, Caylloma)
var OUTSIDE = ['PEDREGAL', 'EL PEDREGAL', 'MAJES', 'CAMANA', 'MOLLENDO', 'ISLAY', 'CHALA', 'CARAVELI', 'YANAQUIHUA'];
var REGION_PROVINCES = ['AREQUIPA', 'CAMANA', 'CARAVELI', 'CASTILLA', 'CAYLLOMA', 'CONDESUYOS', 'ISLAY', 'LA UNION'];
var REPORT_KINDS = ['DENUNCIA', 'REPORTE'];
// How the sheet writes an empty cell
var MISSING = ['NA', 'N/A', 'N A', 'NULL', 'NAN', 'NONE', '#N/A', '#NA', '<NA>'];

/** Web app entry point: returns the totals as JSON. */
function doGet() {
  var cache = CacheService.getScriptCache();
  var json = cache.get(CACHE_KEY);
  if (!json) {
    json = JSON.stringify(buildTotals_());
    cache.put(CACHE_KEY, json, CACHE_SECONDS);
  }
  return ContentService.createTextOutput(json).setMimeType(ContentService.MimeType.JSON);
}

/** Run this from the editor to see what the website will receive (View > Logs). */
function previewTotals() {
  var t = buildTotals_();
  Logger.log(JSON.stringify(t, null, 1));
}

function norm_(s) {
  if (s === null || s === undefined) return '';
  var t = String(s);
  try { t = t.normalize('NFKD').replace(/[̀-ͯ]/g, ''); } catch (e) {
    t = t.replace(/[áàä]/gi, 'a').replace(/[éèë]/gi, 'e').replace(/[íìï]/gi, 'i').replace(/[óòö]/gi, 'o').replace(/[úùü]/gi, 'u').replace(/ñ/gi, 'n');
  }
  t = t.toUpperCase().replace(/[.,]/g, ' ').replace(/\s+/g, ' ').trim();
  return MISSING.indexOf(t) >= 0 ? '' : t;
}

function isoDate_(v, tz) {
  if (v instanceof Date && !isNaN(v)) return Utilities.formatDate(v, tz, 'yyyy-MM-dd');
  if (norm_(v) === '') return null;
  var m = String(v).match(/^\s*(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})/);   // day/month/year, as shown in Lima
  if (m) {
    var d = +m[1], mo = +m[2], y = +m[3];
    var dt = new Date(Date.UTC(y, mo - 1, d));
    if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null;
    return y + '-' + ('0' + mo).slice(-2) + '-' + ('0' + d).slice(-2);
  }
  m = String(v).match(/^\s*(\d{4})-(\d{2})-(\d{2})/);
  return m ? m[1] + '-' + m[2] + '-' + m[3] : null;
}

function buildTotals_() {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(SHEET_NAME);
  var tz = ss.getSpreadsheetTimeZone() || 'America/Lima';
  var last = sheet.getLastRow();
  var header = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(function (h) { return String(h).trim(); });
  function column(name) {
    var i = header.indexOf(name);
    if (i < 0) throw new Error('Column not found: ' + name);
    return last < 2 ? [] : sheet.getRange(2, i + 1, last - 1, 1).getValues().map(function (r) { return r[0]; });
  }
  // Only these six columns are read.
  var act = column('ACTIVIDAD'), fecha = column('FECHA'), ano = column('ANO'),
      prov = column('PROVINCIA'), dist = column('DISTRITO'), taxo = column('TAXO_INSECTO_DENUNCIA');

  var byNorm = {};
  DISTRICTS.forEach(function (d) { byNorm[norm_(d)] = d; });
  Object.keys(ALIASES).forEach(function (k) { byNorm[k] = ALIASES[k]; });

  var districts = {};
  DISTRICTS.forEach(function (d) { districts[d] = {}; });
  var where = {}, confirmed = {}, total = 0, identified = 0, first = null, lastDate = null;
  function add(obj, key) { obj[key] = (obj[key] || 0) + 1; }

  for (var r = 0; r < act.length; r++) {
    if (REPORT_KINDS.indexOf(norm_(act[r])) < 0) continue;
    total++;
    var iso = isoDate_(fecha[r], tz);
    if (iso) { if (!first || iso < first) first = iso; if (!lastDate || iso > lastDate) lastDate = iso; }
    var year = iso ? +iso.slice(0, 4) : null;
    if (year === null) { var a = parseInt(ano[r], 10); year = (a >= 2020 && a <= 2035) ? a : null; }
    var t = norm_(taxo[r]);
    if (t) identified++;
    var isConf = t.indexOf('TRIATOMA INFESTANS') >= 0;
    var p = norm_(prov[r]), d = norm_(dist[r]), bucket;
    if (OUTSIDE.indexOf(d) >= 0) bucket = 'other_provinces_arequipa_region';
    else if (p && p !== 'AREQUIPA') bucket = REGION_PROVINCES.indexOf(p) >= 0 ? 'other_provinces_arequipa_region' : 'other_regions';
    else if (byNorm[d]) bucket = 'province';
    else if (!d) bucket = p === 'AREQUIPA' ? 'province_no_district' : 'no_location';
    else bucket = 'no_location';
    if (bucket === 'province' && year === null) bucket = 'province_no_year';
    add(where, bucket);
    if (isConf) add(confirmed, bucket);
    if (bucket === 'province') {
      var cell = districts[byNorm[d]][String(year)] || (districts[byNorm[d]][String(year)] = [0, 0]);
      cell[0]++;
      if (isConf) cell[1]++;
    }
  }
  var inf = { total: 0 };
  Object.keys(confirmed).forEach(function (k) { inf[k] = confirmed[k]; inf.total += confirmed[k]; });
  return {
    version: 1,
    source: 'Alerta Chirimacha report log (DENUNCIAS tab). District totals only.',
    generated: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    first_report: first,
    last_report: lastDate,
    reports_total: total,
    by_place: where,
    identified_by_team: identified,
    triatoma_infestans: inf,
    districts: districts
  };
}
