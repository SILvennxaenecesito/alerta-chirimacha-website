# Alerta Chirimacha website

Draft website for Alerta Chirimacha, the community surveillance system for chirimachas (*Triatoma infestans*) in Arequipa, Peru. Residents report an insect by WhatsApp; the site also shows where reports come from on a map of the city and the province.

Everything here is a **draft for the team's review**, not the official site yet.

- **Plan:** [PLAN.md](PLAN.md): audience, decisions, site map, data and privacy, the map, open questions.
- **Context for anyone picking up the work:** [HANDOFF.md](HANDOFF.md).

## View the draft

Open `site/index.html` in a browser (keep the `site/` folder together: the page uses `assets/` and `media/`). Spanish is the default; the EN button (or `?lang=en` / `#en` at the end of the address) switches to English.

## Folders

- `site/index.html`: the built page. Don't edit it by hand.
- `site/source/template.html`: the page source. Bilingual text is written as `⟦Español||English⟧` (Spanish first), or `⟪Español||English⟫` inside SVG text.
- `site/source/build.py` and `mapdraw.py`: build `site/index.html`, including the map.
- `site/data/districts.csv`: the 29 districts of Arequipa province, their map labels and INEI ubigeo codes.
- `site/data/reports-by-district.csv`, `reports-summary.json`: report counts by district and year (no personal data).
- `site/data/map/`: the base map layers and their sources ([README](site/data/map/README.md)).
- `site/assets/`, `site/media/`: the team's photo and video (web versions).
- `tools/`: scripts that make the data files.

## Rebuild

From `site/source/` (Python 3, no extra packages):

```
python3 build.py template.html ../data ../index.html
```

## Update the report counts

1. Get the latest report spreadsheet from the team. **Keep it outside this repository**: it has residents' names, phone numbers and addresses.
2. From the repository root (needs pandas and openpyxl):

   ```
   python3 tools/aggregate_reports.py /path/to/Denuncias_Alerta_Chirimacha.xlsx site/data
   ```

   It reads only the date, district and insect columns and writes district totals by year.
3. Rebuild the page.

Only totals per district go into `site/data`: never addresses, names, phone numbers or coordinates of homes.
