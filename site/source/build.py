"""Build the bilingual Alerta Chirimacha draft site.

Run from this folder:
    python3 build.py template.html ../data ../index.html

What it does
  1. Reads ../data/districts.csv (the 29 districts of Arequipa province, map
     labels and INEI ubigeo codes), ../data/reports.json (district totals by
     year, made by tools/aggregate_reports.py or the Google Sheet script) and
     ../data/live.json (address of the Google Sheet script, if set up; the
     page then refreshes its numbers from the sheet on every visit).
  2. Draws the map (mapdraw.py: city view and province view, from the layers
     in ../data/map/) and the table, and fills the @@PLACEHOLDERS@@ in the
     template.
  3. Expands the language macros. Spanish comes first in this site:
       ⟦Español||English⟧   in HTML text   -> <span class="es">…</span><span class="en">…</span>
       ⟪Español||English⟫   in SVG <text>  -> <tspan class="es">…</tspan><tspan class="en">…</tspan>
       attr="⟦Español||English⟧"           -> attr="Español" data-en-attr="English"
       <title>⟦Español||English⟧</title>   -> <title data-en="English">Español</title>
                                              (same for <desc> and <option>)
     The page script swaps the data-en* values when the language changes; CSS
     hides whichever span/tspan is not active.

Privacy: the map only ever shows totals per district. Do not add coordinates
of homes, addresses, names or photo metadata to the data files.
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from html import escape

from mapdraw import build_map

MONTHS_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
             'octubre', 'noviembre', 'diciembre']
MONTHS_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
             'October', 'November', 'December']


def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def load(data_dir):
    districts = read_csv(os.path.join(data_dir, 'districts.csv'))
    names = [d['district'] for d in districts]
    assert len(names) == 29 and len(set(names)) == 29, 'expected the 29 districts of Arequipa province'
    rep = json.load(open(os.path.join(data_dir, 'reports.json'), encoding='utf-8'))
    assert rep.get('version') == 1, 'reports.json: unknown format'
    assert set(rep['districts']) == set(names), 'reports.json: district names do not match districts.csv'
    years = {d: {int(y): v for y, v in rep['districts'][d].items()} for d in names}
    live = json.load(open(os.path.join(data_dir, 'live.json'), encoding='utf-8')).get('url', '').strip()
    assert not live or live.startswith('https://script.google.com/'), 'live.json: expected an Apps Script web app URL'
    return districts, years, rep, live


def month(iso, lang):
    d = date.fromisoformat(iso[:10])
    return f'{MONTHS_ES[d.month - 1]} de {d.year}' if lang == 'es' else f'{MONTHS_EN[d.month - 1]} {d.year}'


def day(iso, lang):
    d = date.fromisoformat(iso[:10])
    return f'{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}' if lang == 'es' else f'{MONTHS_EN[d.month - 1]} {d.day}, {d.year}'


def live(key, value):
    """Numbers and dates the page script refreshes when live data arrives from the Google Sheet."""
    return f'<span data-live="{key}">{value}</span>'


def table_rows(districts, totals):
    out = []
    for d in sorted(districts, key=lambda d: (-totals[d['district']][0], d['district'])):
        n, k = totals[d['district']]
        out.append(f'<tr data-d="{escape(d["district"])}"><th scope="row">{escape(d["district"])}</th>'
                   f'<td class="num">{n}</td><td class="num">{k}</td></tr>')
    return ''.join(out)


def expand(s):
    def attr(m):
        es, en = m[3], m[4]
        assert '"' not in es and '"' not in en, m[0]
        return f'{m[1]}{m[2]}="{es}" data-en-{m[2]}="{en}"'
    s = re.sub(r'(\s)([a-zA-Z][\w:-]*)="⟦([^"⟧]*?)\|\|([^"⟧]*?)⟧"', attr, s)

    def elt(m):
        tag, rest, es, en = m[1], m[2], m[3], m[4]
        assert '"' not in en and '<' not in es + en, m[0]
        return f'<{tag}{rest} data-en="{en}">{es}</{tag}>'
    s = re.sub(r'<(title|desc|option)(\b[^>]*)>⟦(.*?)\|\|(.*?)⟧</\1>', elt, s, flags=re.S)
    s = re.sub(r'⟦(.*?)\|\|(.*?)⟧', r'<span class="es">\1</span><span class="en">\2</span>', s, flags=re.S)
    s = re.sub(r'⟪(.*?)\|\|(.*?)⟫', r'<tspan class="es">\1</tspan><tspan class="en">\2</tspan>', s, flags=re.S)
    assert not re.search('[⟦⟧⟪⟫]', s), 'unexpanded macro'
    return s


def main():
    src, data_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    districts, years, rep, live_url = load(data_dir)
    totals = {d['district']: [sum(v[0] for v in years[d['district']].values()),
                              sum(v[1] for v in years[d['district']].values())] for d in districts}
    labels = {d['district']: d['label'] for d in districts}
    city_svg, prov_svg, meta = build_map(os.path.join(data_dir, 'map'), totals, labels)

    all_years = sorted({y for d in years.values() for y in d})
    n_prov = sum(n for n, _ in totals.values())
    k_prov = sum(k for _, k in totals.values())
    assert n_prov == rep['by_place'].get('province', 0), 'district totals do not match the summary'
    n_all = rep['reports_total']
    data = {
        'years': all_years,
        'nmax': meta['nmax'], 'rmax': meta['rmax'], 'badge': meta['badge'], 'views': meta['views'],
        'districts': [{'d': d['district'], 'u': d['ubigeo'], 'y': years[d['district']]} for d in districts],
        'summary': {'all': n_all, 'province': n_prov, 'outside': n_all - n_prov,
                    'first': rep['first_report'], 'last': rep['last_report'], 'generated': rep['generated']},
        'live': live_url,
    }
    year_opts = ''.join(f'<option value="{y}">{y}</option>' for y in reversed(all_years))
    fills = {
        '@@MAP_CITY@@': city_svg,
        '@@MAP_PROV@@': prov_svg,
        '@@TABLE_ROWS@@': table_rows(districts, totals),
        '@@DATA_JSON@@': json.dumps(data, ensure_ascii=False, separators=(',', ':')),
        '@@YEAR_OPTIONS@@': year_opts,
        '@@N_PROV@@': live('n_prov', n_prov),
        '@@K_PROV@@': live('k_prov', k_prov),
        '@@N_ALL@@': live('n_all', n_all),
        '@@N_OUT@@': live('n_out', n_all - n_prov),
        '@@N_IDENT@@': live('n_ident', rep['identified_by_team']),
        '@@K_ALL@@': live('k_all', rep['triatoma_infestans']['total']),
        '@@FROM_ES@@': live('from_es', month(rep['first_report'], 'es')),
        '@@FROM_EN@@': live('from_en', month(rep['first_report'], 'en')),
        '@@TO_ES@@': live('to_es', month(rep['last_report'], 'es')),
        '@@TO_EN@@': live('to_en', month(rep['last_report'], 'en')),
        '@@UPD_ES@@': live('upd_es', day(rep['generated'], 'es')),
        '@@UPD_EN@@': live('upd_en', day(rep['generated'], 'en')),
        '@@Y0@@': str(all_years[0]), '@@Y1@@': str(all_years[-1]),
    }
    s = open(src, encoding='utf-8').read()
    for k, v in fills.items():
        assert k in s, f'{k} missing from template'
        s = s.replace(k, v)
    s = expand(s)
    assert '@@' not in s, 'unfilled placeholder: ' + re.search(r'@@\w+@@', s)[0]
    open(out, 'w', encoding='utf-8').write(s)
    print(len(s) // 1024, 'KB  map:', len(city_svg) // 1024, 'KB city +', len(prov_svg) // 1024, 'KB province',
          '| live data:', live_url or 'not set (snapshot only)')


if __name__ == '__main__':
    main()
