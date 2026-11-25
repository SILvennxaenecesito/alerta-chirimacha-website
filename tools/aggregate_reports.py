"""Turn the team's report log into district totals for the website (snapshot).

Usage (from the repository root):
    python3 tools/aggregate_reports.py REPORT_LOG site/data

REPORT_LOG can be:
  * the Excel file (sheet DENUNCIAS),
  * the DENUNCIAS tab downloaded from Google Sheets as CSV
    (File > Download > Comma-separated values), or
  * a text export with "## Sheet name: DENUNCIAS" sections.

Writes:
    site/data/reports.json              district totals by year + summary (the page reads this)
    site/data/reports-by-district.csv   the same totals as a table, for people

The live version of this calculation runs inside the Google Sheet
(tools/apps-script/Code.gs) and returns exactly the same JSON. Keep the rules
of both in step.

Privacy
  * Only these columns are used: ACTIVIDAD, FECHA, ANO, PROVINCIA, DISTRITO,
    TAXO_INSECTO_DENUNCIA. Names, phone numbers, addresses, household codes
    (UNICODE) and photo links are never read into the output.
  * Keep the report log itself OUT of this repository and out of any public
    place. Only the two output files belong here.

Rules (check them with the team; see HANDOFF.md)
  * A row counts as a report when ACTIVIDAD is DENUNCIA or REPORTE. The other
    rows log outreach activities (radio interviews, posters, Facebook ads).
  * "confirmed" = TAXO_INSECTO_DENUNCIA says Triatoma infestans (including
    "huevos eclosionados"). Genus-only "Triatoma" is not counted.
  * Report numbers restart in 2022, so repeated NUMERO_DENUNCIA values are
    different reports. Nothing is de-duplicated.
  * DISTRITO = PEDREGAL is El Pedregal, the main town of Majes (Caylloma
    province), even when PROVINCIA says AREQUIPA. It is counted outside the
    province.
  * Rows from other provinces or regions are counted in the summary only.
"""
import csv
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

COLUMNS = ['ACTIVIDAD', 'FECHA', 'ANO', 'PROVINCIA', 'DISTRITO', 'TAXO_INSECTO_DENUNCIA']
REPORT_KINDS = {'DENUNCIA', 'REPORTE'}
REGION_PROVINCES = {'AREQUIPA', 'CAMANA', 'CARAVELI', 'CASTILLA', 'CAYLLOMA', 'CONDESUYOS', 'ISLAY', 'LA UNION'}

# Spellings in the log -> district name used on the site (districts.csv)
ALIASES = {
    'CERCADO': 'Arequipa', 'CERCADO DE AREQUIPA': 'Arequipa',
    'ASA': 'Alto Selva Alegre',
    'HUNTER': 'Jacobo Hunter', 'J HUNTER': 'Jacobo Hunter',
    'JOSE NUIS BUSTAMANTE Y RIVERO': 'José Luis Bustamante y Rivero',
    'BUSTAMANTE Y RIVERO': 'José Luis Bustamante y Rivero', 'JLBYR': 'José Luis Bustamante y Rivero',
    'J L B Y RIVERO': 'José Luis Bustamante y Rivero',
}
# Districts outside Arequipa province that appear without a usable PROVINCIA
OUTSIDE = {'PEDREGAL', 'EL PEDREGAL', 'MAJES', 'CAMANA', 'MOLLENDO', 'ISLAY', 'CHALA', 'CARAVELI', 'YANAQUIHUA'}


# Placeholders for an empty cell. The Google Sheet uses "NA" (pandas reads these as empty in Excel too).
MISSING = {'NA', 'N/A', 'N A', 'NULL', 'NAN', 'NONE', '#N/A', '#NA', '<NA>'}


def norm(s):
    if s is None or (isinstance(s, float) and s != s):
        return ''
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode()
    s = ' '.join(s.upper().replace('.', ' ').replace(',', ' ').split())
    return '' if s in MISSING else s


def parse_date(v):
    """Excel datetimes, or text in day/month/year order (as the sheet shows dates in Lima)."""
    if v is None or (isinstance(v, float) and v != v) or norm(v) == '':
        return None
    if isinstance(v, (datetime, date)):
        return v.date() if isinstance(v, datetime) else v
    if hasattr(v, 'to_pydatetime'):
        return v.to_pydatetime().date()
    m = re.match(r'^\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})', str(v))
    if m:
        d, mo, y = map(int, m.groups())
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    m = re.match(r'^\s*(\d{4})-(\d{2})-(\d{2})', str(v))
    if m:
        return date(*map(int, m.groups()))
    return None


def read_rows(path):
    """Yield dicts with only the needed columns."""
    if path.lower().endswith(('.xlsx', '.xlsm', '.xls')):
        import pandas as pd
        df = pd.read_excel(path, sheet_name='DENUNCIAS', usecols=COLUMNS)
        for rec in df.to_dict('records'):
            yield rec
        return
    text = open(path, encoding='utf-8-sig').read()
    if text.startswith('## Sheet name:'):
        sections = re.split(r'^## Sheet name: *(.+)$', text, flags=re.M)
        named = {sections[i].strip(): sections[i + 1] for i in range(1, len(sections) - 1, 2)}
        text = named['DENUNCIAS']
    reader = csv.reader(io.StringIO(text.strip('\n')))
    header = [h.strip() for h in next(reader)]
    idx = {c: header.index(c) for c in COLUMNS}
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        yield {c: (row[i] if i < len(row) else '') for c, i in idx.items()}


def aggregate(rows, districts):
    by_norm = {norm(d): d for d in districts}
    by_norm.update(ALIASES)
    counts = defaultdict(lambda: [0, 0])          # (district, year) -> [reports, confirmed]
    where, confirmed, unmatched = Counter(), Counter(), Counter()
    dates, total, identified = [], 0, 0
    for row in rows:
        if norm(row['ACTIVIDAD']) not in REPORT_KINDS:
            continue
        total += 1
        when = parse_date(row['FECHA'])
        if when:
            dates.append(when)
        year = when.year if when else None
        if year is None:
            try:
                a = int(float(row['ANO']))
                year = a if 2020 <= a <= 2035 else None
            except (TypeError, ValueError):
                year = None
        taxon = norm(row['TAXO_INSECTO_DENUNCIA'])
        if taxon:
            identified += 1
        is_conf = 'TRIATOMA INFESTANS' in taxon
        prov, dist = norm(row['PROVINCIA']), norm(row['DISTRITO'])
        if dist in OUTSIDE:
            bucket = 'other_provinces_arequipa_region'
        elif prov and prov != 'AREQUIPA':
            bucket = 'other_provinces_arequipa_region' if prov in REGION_PROVINCES else 'other_regions'
        elif dist in by_norm:
            bucket = 'province'
        elif not dist:
            bucket = 'province_no_district' if prov == 'AREQUIPA' else 'no_location'
        else:
            bucket = 'no_location'
            unmatched[dist] += 1
        if bucket == 'province' and year is None:
            bucket = 'province_no_year'
        where[bucket] += 1
        if is_conf:
            confirmed[bucket] += 1
        if bucket == 'province':
            c = counts[(by_norm[dist], year)]
            c[0] += 1
            c[1] += int(is_conf)
    out_d = {d: {} for d in districts}
    for (d, y), v in counts.items():
        out_d[d][str(y)] = v
    for d in out_d:
        out_d[d] = dict(sorted(out_d[d].items()))
    return {
        'version': 1,
        'source': 'Alerta Chirimacha report log (DENUNCIAS tab). District totals only.',
        'generated': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'first_report': min(dates).isoformat(),
        'last_report': max(dates).isoformat(),
        'reports_total': total,
        'by_place': dict(where),
        'identified_by_team': identified,
        'triatoma_infestans': {'total': sum(confirmed.values()), **dict(confirmed)},
        'districts': out_d,
    }, unmatched


def main():
    src, data_dir = sys.argv[1], sys.argv[2]
    districts = [r['district'] for r in csv.DictReader(open(os.path.join(data_dir, 'districts.csv'), encoding='utf-8'))]
    result, unmatched = aggregate(read_rows(src), districts)
    with open(os.path.join(data_dir, 'reports.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
        f.write('\n')
    with open(os.path.join(data_dir, 'reports-by-district.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['district', 'year', 'reports', 'confirmed'])
        for d in districts:
            for y, (n, k) in result['districts'][d].items():
                w.writerow([d, y, n, k])
    summary = {k: v for k, v in result.items() if k != 'districts'}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if unmatched:
        print('Unmatched district spellings (counted as no_location):', dict(unmatched))


if __name__ == '__main__':
    main()
