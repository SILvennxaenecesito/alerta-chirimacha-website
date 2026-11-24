"""Build the bilingual Alerta Chirimacha draft site.

Run from this folder:
    python3 build.py template.html ../data ../index.html

What it does
  1. Reads ../data/districts.csv (the 29 districts of Arequipa province, map
     labels and INEI ubigeo codes) and the report counts made by
     tools/aggregate_reports.py:
       ../data/reports-by-district.csv   district, year, reports, confirmed
       ../data/reports-summary.json      date range and totals
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
    years = defaultdict(dict)
    for r in read_csv(os.path.join(data_dir, 'reports-by-district.csv')):
        assert r['district'] in names, f'unknown district {r["district"]!r}'
        years[r['district']][int(r['year'])] = [int(r['reports']), int(r['confirmed'])]
    summary = json.load(open(os.path.join(data_dir, 'reports-summary.json'), encoding='utf-8'))
    return districts, years, summary


def month(iso, lang):
    d = date.fromisoformat(iso)
    return f'{MONTHS_ES[d.month - 1]} de {d.year}' if lang == 'es' else f'{MONTHS_EN[d.month - 1]} {d.year}'


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
    districts, years, summary = load(data_dir)
    totals = {d['district']: [sum(v[0] for v in years[d['district']].values()),
                              sum(v[1] for v in years[d['district']].values())] for d in districts}
    labels = {d['district']: d['label'] for d in districts}
    city_svg, prov_svg, meta = build_map(os.path.join(data_dir, 'map'), totals, labels)

    all_years = sorted(int(y) for y in summary['province_reports_by_year'])
    n_prov = sum(n for n, _ in totals.values())
    k_prov = sum(k for _, k in totals.values())
    assert n_prov == summary['by_place']['province'], 'district totals do not match the summary'
    n_all = summary['reports_total']
    data = {
        'years': all_years,
        'nmax': meta['nmax'], 'rmax': meta['rmax'], 'badge': meta['badge'], 'views': meta['views'],
        'districts': [{'d': d['district'], 'u': d['ubigeo'], 'y': years[d['district']]} for d in districts],
        'summary': {'all': n_all, 'province': n_prov, 'outside': n_all - n_prov,
                    'first': summary['first_report'], 'last': summary['last_report']},
    }
    year_opts = ''.join(f'<option value="{y}">{y}</option>' for y in reversed(all_years))
    fills = {
        '@@MAP_CITY@@': city_svg,
        '@@MAP_PROV@@': prov_svg,
        '@@TABLE_ROWS@@': table_rows(districts, totals),
        '@@DATA_JSON@@': json.dumps(data, ensure_ascii=False, separators=(',', ':')),
        '@@YEAR_OPTIONS@@': year_opts,
        '@@N_PROV@@': str(n_prov),
        '@@K_PROV@@': str(k_prov),
        '@@N_ALL@@': str(n_all),
        '@@N_OUT@@': str(n_all - n_prov),
        '@@N_IDENT@@': str(summary['identified_by_team']),
        '@@K_ALL@@': str(summary['triatoma_infestans']['total']),
        '@@FROM_ES@@': month(summary['first_report'], 'es'),
        '@@FROM_EN@@': month(summary['first_report'], 'en'),
        '@@TO_ES@@': month(summary['last_report'], 'es'),
        '@@TO_EN@@': month(summary['last_report'], 'en'),
        '@@Y0@@': str(all_years[0]), '@@Y1@@': str(all_years[-1]),
    }
    s = open(src, encoding='utf-8').read()
    for k, v in fills.items():
        assert k in s, f'{k} missing from template'
        s = s.replace(k, v)
    s = expand(s)
    assert '@@' not in s, 'unfilled placeholder: ' + re.search(r'@@\w+@@', s)[0]
    open(out, 'w', encoding='utf-8').write(s)
    print(len(s) // 1024, 'KB  map:', len(city_svg) // 1024, 'KB city +', len(prov_svg) // 1024, 'KB province')


if __name__ == '__main__':
    main()
