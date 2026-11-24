"""Turn the team's report spreadsheet into district totals for the website.

Usage (from the repository root):
    python3 tools/aggregate_reports.py /path/to/Denuncias_Alerta_Chirimacha.xlsx site/data

Reads the DENUNCIAS sheet and writes two small files:
    site/data/reports-by-district.csv   district, year, reports, confirmed
    site/data/reports-summary.json      date range and totals (no personal data)

Privacy
  * Only these columns are loaded: ACTIVIDAD, FECHA, ANO, PROVINCIA, DISTRITO,
    TAXO_INSECTO_DENUNCIA. Names, phone numbers, addresses and photo links are
    never read, so they cannot end up in the output.
  * Keep the spreadsheet itself OUT of this repository and out of any public
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
import json
import os
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date

import pandas as pd

COLUMNS = ['ACTIVIDAD', 'FECHA', 'ANO', 'PROVINCIA', 'DISTRITO', 'TAXO_INSECTO_DENUNCIA']
REPORT_KINDS = {'DENUNCIA', 'REPORTE'}
REGION_PROVINCES = {'AREQUIPA', 'CAMANA', 'CARAVELI', 'CASTILLA', 'CAYLLOMA', 'CONDESUYOS', 'ISLAY', 'LA UNION'}

# Spellings in the spreadsheet -> district name used on the site (districts.csv)
ALIASES = {
    'CERCADO': 'Arequipa', 'CERCADO DE AREQUIPA': 'Arequipa',
    'ASA': 'Alto Selva Alegre',
    'HUNTER': 'Jacobo Hunter', 'J HUNTER': 'Jacobo Hunter',
    'JOSE NUIS BUSTAMANTE Y RIVERO': 'José Luis Bustamante y Rivero',
    'BUSTAMANTE Y RIVERO': 'José Luis Bustamante y Rivero', 'JLBYR': 'José Luis Bustamante y Rivero',
    'J L B Y RIVERO': 'José Luis Bustamante y Rivero',
}
# Districts outside Arequipa province that appear without a usable PROVINCIA
OUTSIDE = {
    'PEDREGAL': 'region', 'EL PEDREGAL': 'region', 'MAJES': 'region',  # Caylloma
    'CAMANA': 'region', 'MOLLENDO': 'region', 'ISLAY': 'region', 'CHALA': 'region',
    'CARAVELI': 'region', 'YANAQUIHUA': 'region',
}


def norm(s):
    if s is None or (isinstance(s, float) and s != s):
        return ''
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode()
    s = s.upper().replace('.', ' ').replace(',', ' ')
    return ' '.join(s.split())


def main():
    xlsx, data_dir = sys.argv[1], sys.argv[2]
    districts = [r['district'] for r in csv.DictReader(open(os.path.join(data_dir, 'districts.csv'), encoding='utf-8'))]
    by_norm = {norm(d): d for d in districts}
    by_norm.update(ALIASES)

    df = pd.read_excel(xlsx, sheet_name='DENUNCIAS', usecols=COLUMNS)
    df = df[df['ACTIVIDAD'].map(norm).isin(REPORT_KINDS)].copy()
    dates = pd.to_datetime(df['FECHA'], errors='coerce')

    counts = defaultdict(lambda: [0, 0])          # (district, year) -> [reports, confirmed]
    where = Counter()
    unmatched = Counter()
    confirmed = Counter()
    years_seen = Counter()
    for (_, row), when in zip(df.iterrows(), dates):
        year = when.year if pd.notna(when) else None
        if year is None:
            a = row['ANO']
            year = int(a) if pd.notna(a) and 2020 <= int(a) <= 2030 else None
        prov, dist = norm(row['PROVINCIA']), norm(row['DISTRITO'])
        is_conf = 'TRIATOMA INFESTANS' in norm(row['TAXO_INSECTO_DENUNCIA'])

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

        where[bucket] += 1
        if is_conf:
            confirmed[bucket] += 1
        if bucket == 'province':
            if year is None:
                where['province_no_year'] += 1
                continue
            years_seen[year] += 1
            c = counts[(by_norm[dist], year)]
            c[0] += 1
            c[1] += int(is_conf)

    out_csv = os.path.join(data_dir, 'reports-by-district.csv')
    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['district', 'year', 'reports', 'confirmed'])
        for (d, y), (n, k) in sorted(counts.items(), key=lambda kv: (districts.index(kv[0][0]), kv[0][1])):
            w.writerow([d, y, n, k])

    ok = dates.dropna()
    summary = {
        'source': 'Alerta Chirimacha report log (team spreadsheet, kept outside this repository)',
        'generated': date.today().isoformat(),
        'first_report': ok.min().date().isoformat(),
        'last_report': ok.max().date().isoformat(),
        'reports_total': int(len(df)),
        'by_place': dict(where),
        'identified_by_team': int(df['TAXO_INSECTO_DENUNCIA'].notna().sum()),
        'triatoma_infestans': {'total': int(sum(confirmed.values())), **dict(confirmed)},
        'province_reports_by_year': {str(y): years_seen[y] for y in sorted(years_seen)},
    }
    with open(os.path.join(data_dir, 'reports-summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if unmatched:
        print('Unmatched district spellings (counted as no_location):', dict(unmatched))


if __name__ == '__main__':
    main()
