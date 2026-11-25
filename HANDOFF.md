# Handoff: Alerta Chirimacha website

Read this first in any new task on this project. Updated 2026-11-25. Prepared by Sil Necesito (volunteer research assistant) for Dr. Michael Z. Levy and the Alerta Chirimacha team.

> This repository is shared with the team. Commit messages, pull requests and notes here are written for the team. Keep them professional: no personal notes.

## 1. What this project is

Alerta Chirimacha is the lab's community reporting system for chirimachas in Arequipa: residents send photos of suspected insects by WhatsApp, the team identifies them, and confirmed findings lead to neighborhood alerts on Facebook. In the Nov 18 planning meeting the team made the Alerta Chirimacha website the **priority project**, ahead of the lab homepage.

Related repository: `SILvennxaenecesito/levy-lab-website` (lab homepage drafts and the "Immune System for the City" explainer).

| Deliverable | Path | Status |
|---|---|---|
| Site plan | `PLAN.md` | Draft v3 for team review |
| One-page site, Spanish first with English toggle | `site/index.html` (built from `site/source/`) | Draft v3: whole-insect photo, iNaturalist links, live numbers (once the sheet script is deployed), real map, video |
| Report counts (snapshot) | `site/data/reports.json` (+ `reports-by-district.csv` for people) | From the report log, Oct 3, 2020 – Nov 11, 2026 |
| Live numbers from the Google Sheet | `tools/apps-script/` | Ready to deploy; the sheet owner sets it up once (about 5 minutes, see its README) |
| Base map | `site/data/map/` | INEI + OpenStreetMap + Terrain Tiles (see its README) |

## 2. Requirements and decisions

**From the Nov 18 planning meeting**
- People now find Alerta Chirimacha mainly by searching online, so a real website is needed. It should be a website, not an app.
- Main page for people reporting ("reporta tu chirimacha"), plus "see our reports" as a map.
- **Decision:** reporting links to the WhatsApp number instead of a web form.
- **Decision:** reports are mapped at the district level, not by locality.
- Keep the Facebook page's color scheme; adapt its content.
- Use the team's existing Spanish video. No new videos.
- About 95% of reported insects are not chirimachas. The look-alike gallery idea was dropped.
- Keep text short.
- Later: Alerta Chirimacha might run in Texas when the Texas project starts.

**From the Nov 4 meeting:** no self-identification needed; district-level data only, never household locations or names.

**From the review of draft v1 (Nov 23):** use a real chirimacha photo from the Facebook alert; a real map that shows the geography with the reports highlighted; Texas A&M's "Found a bug?" page as a reference.

**From the review of draft v2 (Nov 25):** show the whole insect, legs included, in both photos; link iNaturalist so people can compare their insect with real chirimachas; connect the page to the team's Google Sheet so new reports show up on their own.

## 3. Content rules

1. **No fabricated data.** Numbers on the page come from the team's report log: live from the Google Sheet script (`tools/apps-script/Code.gs`) when it is set up, otherwise from the snapshot made by `tools/aggregate_reports.py`. Both use the same rules and return the same totals. The page says that these are real team data to confirm before publishing.
2. **Privacy:** only totals per district. No addresses, names, phone numbers of reporters, coordinates of homes or photo metadata. The report spreadsheet never goes into this repository or any public place; `.gitignore` blocks spreadsheet files. The Google Sheet stays private: never "anyone with the link", never "publish to web". The sheet script is the only way data leaves it, and it returns district totals only. Don't put the sheet's link or ID in this repository.
3. Keep the **draft banner** until the team approves the site.
4. **No logos** (Penn, UPCH, Gerencia Regional de Salud, or the Alerta Chirimacha mark) in the site's own design until the team confirms which may be used. Partner names stay marked *por confirmar*. (The team's video ends with its own partner logos; that is their material.)
5. The only contact channels are the program's WhatsApp number (989 279 579, to be confirmed) and the Facebook page https://www.facebook.com/AlertaChirimacha/. This differs from the lab-site drafts, which carry no phone numbers; for this site the team chose WhatsApp.
6. Spanish first, English toggle. Short sentences.
7. Health and safety wording (handling insects, cleaning, bites) stays marked *por confirmar* until the team approves it. It follows CDC and Texas A&M guidance.
8. No generated photos or videos; use the team's own material, with credit.
9. Map credits stay under the map and in the footer (INEI/perugeopkg CC BY-SA 4.0, OpenStreetMap ODbL, Terrain Tiles).

## 4. How the site is built

- `site/source/template.html`: edit this, not `index.html`. Bilingual macros are Spanish first: `⟦Español||English⟧` in HTML, `⟪Español||English⟫` in SVG text, `attr="⟦…||…⟧"` for attributes, and `<title>/<desc>/<option>⟦…||…⟧`. Note: the lab-site repo uses English first.
- `site/source/build.py`: reads `site/data/districts.csv`, `reports.json` and `live.json`, checks the district names and that the district totals match the summary, fills the numbers into the text (each one marked `data-live` so the page can refresh it), builds the table, and expands the macros. Run from `site/source/`: `python3 build.py template.html ../data ../index.html`. Standard library only.
- `site/source/mapdraw.py`: draws the city and province views as SVG from `site/data/map/*.geojson`: elevation bands, built-up area, rivers, roads, district boundaries (click targets), volcano and Plaza de Armas markers, district labels placed to avoid overlaps, and report circles. Circle area is proportional to reports, on one scale for all years; the magenta badge shows confirmed *T. infestans*.
- Page script: language toggle; city/province views; zoom (+/−, double-click, drag when zoomed; labels and circles shrink a little as you zoom so the map stays readable; names hide when too small to read); year filter; selection panel with reports per year; table sorted by the current filter; video chapters.
- Live numbers: if `site/data/live.json` has the script's address, the page asks it for the totals on every visit (10-second limit) and updates the counts, dates, circles, table, year list and "Datos al" date. If the answer is missing or not in the expected format (version 1), the page keeps the snapshot. Tested with a mock of the script, including Google's redirect, errors, wrong formats and a timeout.
- `site/assets/chirimacha.jpg` (580×884): cropped from the cover banner of the Alerta Chirimacha Facebook page and turned so the head points up. All six legs are whole; the antenna tips touch the edge because the banner cuts them off. No tag over the photo any more. No EXIF data. The numbered markers in "Recognize it" are placed for this crop (head, antenna, body, striped edge).
- `site/media/`: the team's video re-encoded for the web (720p H.264, 7 MB), a poster frame and four chapter thumbnails. Chapters: 0:00, 0:34, 1:04, 1:43 (the full video is the four parts joined, minus three end cards).
- `tools/aggregate_reports.py`: report log (Excel file, CSV download of the DENUNCIAS tab, or a text export) → `site/data/reports.json` and `reports-by-district.csv`. Rules in its docstring and in PLAN.md. Treats `NA`/`NULL` cells as empty.
- `tools/apps-script/Code.gs`: the same calculation inside the Google Sheet, served as a web app (setup in `tools/apps-script/README.md`). Checked against the snapshot: identical totals with dates stored as text or as real dates.
- `tools/prepare_map_layers.py` and `tools/map-layers-browser.js`: rebuild the base map (see `site/data/map/README.md`).
- Language: Spanish by default; the choice is remembered in the browser; `?lang=en` or `#en` opens English.
- External requests: Google Fonts (text falls back to system fonts) and, once set up, the sheet script on Google's servers. Links to Facebook, WhatsApp, iNaturalist, the study and the sources.

## 5. Verified facts used on the page

- Tamayo LD, Condori-Pino CE, Sanchez Z, Gonçalves R, Málaga Chávez FS, Castillo-Neyra R, Levy MZ, Paz-Soldan VA. *PLOS NTD* 17(10), 2023. https://doaj.org/article/b79d628a9df244229518f3d67ce0c716. First 26 months: 206 reports, 11 (5.3%) confirmed *T. infestans*, no *T. cruzi* found; 57% more confirmed reports than the traditional system; 10% more infested houses than active and passive surveillance combined.
- Report log, Google Sheet export of Nov 25 (Oct 3, 2020 – Nov 11, 2026): 716 reports; 444 with a district in Arequipa province; 20 from other provinces of the region, 33 from other regions, 14 in the province without a district, 205 without a location; 28 confirmed *T. infestans* in the province (29 in all, one from another region); 496 insects identified by the team. Same totals from the Excel logic and from the sheet script.
- iNaturalist: the page links to the observations of the account `lauratamayo` (photo grid in "Recognize it" and the FAQ, map under the reports map), as Sil asked. Not checked from here: iNaturalist blocks automated visits.
- Texas A&M "Found a bug?" (https://kissingbug.tamu.edu/found-a-bug/): don't touch with bare hands, use a glove or small plastic bag; keep it in a closed bag, vial or container; record date, time, indoors or outdoors and possible bites; squashed bugs: pick up with a bag, clean with a bleach solution following the label; identification traits (cone-shaped head, thin antennae and legs, dark body, striped edge, active at night, bites usually painless). Its line that no other insects carry the parasite was not used: Salazar et al. 2015 (*Am J Trop Med Hyg* 92:331–335, Levy lab) showed bed bugs transmitting *T. cruzi* in the laboratory.
- CDC (triatomine bug FAQs): don't touch or squash a suspected triatomine; place a container over it and slide it inside. https://www.cdc.gov/parasites/chagas/gen_info/vectors
- Arequipa province has 29 districts. All 29 ubigeo codes in `districts.csv` (040101–040129) match INEI's district list (checked against the IDDIST field of the INEI-2007 boundaries).
- Example alert (Facebook, April 13, 2026): Loma Verde, Santa Martha and Ampliación Pampas del Cusco, Jacobo Hunter district.
- Volcano heights from OpenStreetMap: El Misti 5822 m, Chachani 6057 m, Pichu Pichu 5664 m.

## 6. Open items

**Waiting on the team** (also in PLAN.md)
- [ ] Confirm the WhatsApp number and the wording of "what happens next".
- [ ] Approve publishing the counts, and the counting rules (DENUNCIA/REPORTE rows, "confirmed" = *T. infestans*, Pedregal = Majes). Group very small counts?
- [ ] Safety wording (bag or glove, closed container, bleach, bites). Keep or freeze the insect for pickup?
- [ ] Original file and credit for the photo (now the Facebook cover banner); credits for the video.
- [ ] Deploy the sheet script (the sheet owner, about 5 minutes: `tools/apps-script/README.md`), then put its address in `site/data/live.json` and rebuild. Until then the page shows the Nov 25 snapshot.
- [ ] iNaturalist: check with the account owner that the site may link the observations, and that their locations are obscured (geoprivacy), because iNaturalist's map shows where each insect was found. If they are not, drop the map link or obscure the observations first.
- [ ] Partner names and logos; full alert list or Facebook link only.
- [ ] Hosting and domain.

**Next drafting steps**
- [ ] Spanish review by native speakers; test on low-end Android phones (the page is about 270 KB plus the photo; the video loads only when played).
- [ ] Optional: photos of harmless look-alikes once approved.
- [ ] Optional: pinch-to-zoom on phones (now: +/− buttons and drag).

## 7. Change log

**2026-11-25 (draft v3)**: Whole-insect photo from the Facebook cover banner in the hero and in "Recognize it" (no more tag; markers moved). iNaturalist: a "compare your insect" box with a link to the photos, a FAQ entry, a link under the map and in the sources. Live numbers: Google Apps Script for the report sheet (district totals only) and page code that refreshes counts, dates, circles, table and years from it, with the snapshot as fallback. `aggregate_reports.py` now reads the Google Sheet export and writes `reports.json`; counts updated to Nov 11, 2026 (716 reports, 444 in the province).

**2026-11-23 (draft v2)**: Real photo from the team's Facebook alert in the hero and in a new "Recognize it" section with numbered features. Steps and identification guide adapted from Texas A&M's "Found a bug?" page; note on squashed insects. Real map replacing the hexagons: INEI districts, OpenStreetMap streets/rivers/built-up area, elevation bands, volcanoes; city and province views, zoom, year filter, badges for confirmed chirimachas, reports-per-year panel. Real counts from the report log via `tools/aggregate_reports.py`; sample data removed. The team's video with four chapters. Sources and map credits.

**2026-11-23 (draft v1)**: Repository started. Added PLAN.md, HANDOFF.md, README.md, and draft v1 of the site: report-by-WhatsApp hero, three steps, short facts, a district hexagon map with sample data, an alert example, video slots, FAQ, an about section, and an English toggle.
