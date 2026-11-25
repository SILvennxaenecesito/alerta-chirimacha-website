# Live numbers from the Google Sheet

The website's map and counts can update on their own when the team adds a row to the report log
("Denuncias Alerta Chirimacha", tab `DENUNCIAS`). A small Google Apps Script, attached to the sheet,
counts the reports and hands the website **only district totals by year**. The sheet stays private.

```
Google Sheet (private)  ──►  Apps Script web app  ──►  website (counts, map, table)
names, phones, addresses      totals per district       nothing personal ever leaves the sheet
```

If the script is not set up, or Google is down, the site shows the last snapshot that was built
into the page (`site/data/reports.json`). Nothing breaks.

## Set it up (once, about 5 minutes)

Do this with the Google account that owns the sheet (or an editor the team trusts).

1. Open the sheet. Menu **Extensiones → Apps Script** (English: Extensions → Apps Script).
2. Delete the sample code in `Code.gs` and paste in the whole of [`Code.gs`](Code.gs) from this folder.
   Save (disk icon). Name the project "Alerta Chirimacha – totales".
3. Optional check: pick `previewTotals` in the function menu, press **Ejecutar** (Run), allow access when
   Google asks, then open **Registro de ejecución** (Execution log). You should see the same totals as the
   website, and no names or phone numbers.
4. **Implementar → Nueva implementación** (Deploy → New deployment). Gear icon → **Aplicación web** (Web app).
   - Descripción: `totales para el sitio web`
   - Ejecutar como: **Yo** (Me)
   - Quién tiene acceso: **Cualquier persona** (Anyone)
   Press **Implementar** and allow access.
5. Copy the **URL de la aplicación web**. It looks like `https://script.google.com/macros/s/AKfy…/exec`.
   Open it in a browser: you should see a short block of numbers (JSON), nothing else.
6. Put the URL in `site/data/live.json`:
   ```json
   {"url": "https://script.google.com/macros/s/AKfy…/exec"}
   ```
   then rebuild the page from `site/source`:
   ```
   python3 build.py template.html ../data ../index.html
   ```

From then on, every visit to the site asks the script for the numbers. The script recomputes at most every
10 minutes, so a new row appears on the site within about 10 minutes.

### "Anyone" means the totals are public, not the sheet

"Cualquier persona" lets the website read what the script returns: the same district totals the site already
shows. It does **not** share the sheet. Some university or work Google accounts block "Anyone"; if the option is
missing, deploy from a personal account that has edit access to the sheet, or ask the account's admin.

### When you change the script

Edit `Code.gs` in the Apps Script editor, then **Implementar → Gestionar implementaciones → editar (lápiz) →
Versión: Nueva versión → Implementar**. This keeps the same URL. A *new* deployment would give a new URL, and
then `live.json` has to change too.

## Rules the script follows

The same as [`tools/aggregate_reports.py`](../aggregate_reports.py), which makes the snapshot. If you change one,
change the other.

- Counts rows whose `ACTIVIDAD` is `DENUNCIA` or `REPORTE`.
- "Confirmed" means `TAXO_INSECTO_DENUNCIA` contains *Triatoma infestans*.
- Only districts of Arequipa province go on the map. El Pedregal is in Majes (Caylloma), so it is counted
  outside the province even when `PROVINCIA` says Arequipa.
- Spellings like `CERCADO`, `ASA` or `HUNTER` are matched to the district names on the map.
- Empty cells written as `NA` or `NULL` count as empty.
- Dates can be real dates or text like `25/11/2026` (day/month/year).
- It reads only six columns: `ACTIVIDAD`, `FECHA`, `ANO`, `PROVINCIA`, `DISTRITO`, `TAXO_INSECTO_DENUNCIA`.
  It finds them by their header, so the column order can change, but the headers must keep these names.

## Privacy

- Never change `doGet` to return rows, names, phone numbers, addresses, household codes (`UNICODE`) or photo links.
- Never use **Archivo → Compartir → Publicar en la web** on the sheet, and never make the sheet "anyone with the link".
- If the sheet moves to a new file, attach the script to the new file and redeploy.
