# Alerta Chirimacha website: plan

Draft v3, November 2026, for review by the Alerta Chirimacha team. Everything here is a proposal; the open questions at the end need the team's answers before launch.

## Why a website

- People now find Alerta Chirimacha by searching online, more than through flyers or Facebook ads. A real website lets them find the reporting number quickly (Nov 18 planning meeting).
- A website, not an app: residents rarely download apps (limited phone storage, slow internet, and many single-disease apps already).

## Who it is for

1. **Residents of Arequipa who found an insect** (main audience). Spanish speakers on phones, sometimes with slow connections. They need one thing: how to report, right away.
2. **People curious about results.** Where reports come from, on a real map of the city and the province.
3. **Partners and researchers.** A short "about" section and a link to the published study.

## Decisions so far

From the Nov 18 planning meeting:
- Reporting links to the **WhatsApp number**, not a web form. People want to know that someone will answer.
- Reports are mapped at the **district level**. Most reports only record district and province, and aggregating protects the people who report.
- The site uses the **color scheme of the Facebook page**, and its content is adapted from the Facebook page.
- The team's existing **Spanish video** goes on the page. No new videos are made.
- **Short text.** Other reporting sites were judged to carry too much information.
- A gallery of look-alike insects was dropped: people don't look closely at bugs. The draft keeps one sentence on look-alikes instead.

From the review of draft v1:
- Use a **real photo** of a chirimacha (from the team's Facebook alert), not an illustration.
- Use a **real map** where people can see the geography, with the reports highlighted, instead of the schematic hexagons.
- Use other programs' guidance as a reference, in particular Texas A&M's ["Found a bug?"](https://kissingbug.tamu.edu/found-a-bug/) page.

From the review of draft v2:
- Show the **whole insect**, legs included, in both photos.
- Link **iNaturalist**, so people can check their insect against real chirimachas.
- Connect the page to the team's **Google Sheet**, so new reports show up without anyone rebuilding the site.

## Site map

One page, Spanish first, with an English toggle. On phones, a "Reportar por WhatsApp" bar stays at the bottom once the visitor scrolls past the first button.

| # | Section | What it does |
|---|---|---|
| 1 | Report (top) | "¿Encontraste una chirimacha?", the WhatsApp button and the number in large type, and the team's photo of a whole adult chirimacha. "Free · No app needed · We never publish names or addresses." |
| 2 | How to report | Three steps adapted from Texas A&M: don't touch it (catch it with a bag or glove, keep it closed in a jar or bag); note when and where (date, time, inside or outside, possible bites); photo and WhatsApp with your district. A note on squashed insects. What happens next. How many of the insects the team identified were chirimachas (29 of 496 as of November 2026). |
| 3 | Recognize it | The photo with numbered features: cone-shaped head, thin antennae and legs, flat dark body, striped edge. Three short facts (night, hiding places, wingless young), one sentence on look-alikes, and a link to compare with real photos on iNaturalist. |
| 4 | Reports by district | Real map: elevation, built-up area, Río Chili, main roads, volcanoes and district boundaries. A circle per district (bigger = more reports) with a badge for confirmed chirimachas. City and province views, zoom, a year filter, a panel with reports per year, a table, and a privacy note. |
| 5 | Alerts | How neighborhood alerts work, the latest alert, and a link to all alerts on Facebook. |
| 6 | Video | The team's animated video (2 min 17 s) with four chapters. |
| 7 | FAQ | Cost, apps, privacy, how to tell if it's a chirimacha, what if it isn't one, a squashed insect, a bite. |
| 8 | About | What Alerta Chirimacha is, who runs it, the 2023 study, other sources. Footer with the slogan, WhatsApp, Facebook and map credits. |

## Data and privacy

- The site shows **only totals per district**: never homes, addresses, names or phone numbers. Each circle sits in the middle of its district's built-up area, not on a home.
- `tools/aggregate_reports.py` reads the team's report log (Excel, CSV or Google Sheet export) and writes `site/data/reports.json` (totals by district and year, date range, summary), plus the same totals as `reports-by-district.csv`. It uses only the activity, date, year, province, district and insect-identification columns, so names, phone numbers and addresses never reach the output.
- **Live numbers.** A Google Apps Script attached to the report sheet (`tools/apps-script/`) does the same calculation and serves the result as a small web app. The page asks it for the totals on each visit, so a new row shows up within about 10 minutes. If the script can't be reached, the page shows the snapshot built into it. The script returns only totals; the sheet itself stays private (never "anyone with the link", never "publish to web"). With the script on, each visit also contacts Google, as it already does for the fonts.
- **The spreadsheet itself never goes into this repository** (it has residents' names, phones and addresses). `.gitignore` blocks spreadsheet files as a safeguard.
- Counting rules (to confirm with the team): a report is a row whose activity is DENUNCIA or REPORTE; "confirmed" means the team identified *Triatoma infestans*; DISTRITO = PEDREGAL is El Pedregal in Majes (Caylloma), outside the province; report numbers restart in 2022, so nothing is de-duplicated.
- The current snapshot (Google Sheet export of November 25) covers October 3, 2020 to November 11, 2026: 716 reports, 444 with a district in Arequipa province (28 confirmed *T. infestans*), 272 from other provinces, other regions or with no district.
- **Photos (later).** Following the meeting, only photos of reported insects that are not dangerous. Before publishing: remove location metadata (EXIF/GPS) and crop out anything that could identify a home.

## The map

Option A from draft v1, now with real geography: our own map, drawn at build time from four open sources, with the lab's district counts on top.

- District boundaries: INEI, via perugeopkg (CC BY-SA 4.0).
- Streets, rivers, lakes, built-up area, volcanoes, Plaza de Armas: OpenStreetMap (ODbL), via OpenFreeMap vector tiles.
- Elevation bands: Terrain Tiles on AWS Open Data (SRTM).

Why not a tile map (Google Maps, Leaflet with OpenStreetMap tiles): the page would depend on outside servers and send every visitor's address to them, it would be heavier on slow phones, and it would not work in the review previews. The built map is plain SVG inside the page, with no API keys and no tracking. If the team later wants street-level detail, a tile map can be added as an extra view.

Not chosen: the lab's own georeferences (very few reports have localities) and an iNaturalist embed (it would load iNaturalist's map and scripts into the page). Instead the page links to the iNaturalist observations, for comparing photos.

## How it is built

- One HTML page (about 270 KB, of which the map is 190 KB) plus the photo (100 KB) and the video (7 MB, loaded only when played). No server of our own, no database, no tracking. The live numbers come from the Apps Script on Google's servers.
- Source: `site/source/template.html` (bilingual text as `⟦Español||English⟧`), `site/source/build.py` and `site/source/mapdraw.py`. The build needs only Python.
- Hosting options are the same as for the lab site: GitHub Pages, a Penn alias, or a domain the lab owns. This is not decided yet. At launch: remove the draft banner and the `noindex` tag, and add the site's address to the Facebook page. The video could also live on YouTube or Facebook to save bandwidth.

## Phases

1. **Draft v1:** structure, Spanish and English copy, sample map.
2. **Drafts v2 and v3 (this pull request):** real photo, real map with the team's counts, video with chapters, steps and identification guide adapted from Texas A&M. v3: the whole insect in both photos, iNaturalist links, live numbers from the team's Google Sheet.
3. **Team review:** confirm the counting rules and publishing the counts, the safety wording, credits for the photo and video, partner names. Spanish review by native speakers; test on low-end Android phones.
4. **Launch:** hosting decision; remove the draft banner after approval; link from the Facebook page.
5. **Later:** photos of reported insects that are not dangerous; a Texas version if Alerta Chirimacha starts there.

## Open questions for the team

1. Is **989 279 579** the right WhatsApp number to publish?
2. Can the real counts be published as shown (all reports by district and year, plus confirmed *T. infestans*)? Should very small counts be grouped ("1–2")?
3. Are the counting rules above right (which rows count as reports, what "confirmed" means, Pedregal = Majes)?
4. Safety wording: catching the insect with a bag or glove, the closed container, cleaning a squashed insect with bleach, the bite advice. Should residents also keep or freeze the insect for pickup (Texas A&M suggests freezing)?
5. What happens after a report is confirmed? The draft says: "we arrange an inspection of your home and alert your neighbors" (marked *por confirmar*).
6. Photo: who took the photo on the Facebook page's cover banner, and can we have the original file? The draft crops it from the banner.
7. Video credits and version (the end card shows the Arequipa regional government and health office).
8. Which partner names (and logos, if any) can appear?
9. Show the full list of neighborhood alerts on the site, or only link to Facebook?
10. Hosting and domain.
11. Live numbers: who can deploy the sheet script (the sheet owner, about 5 minutes)? Is it fine that the district totals are served publicly from Google, as they are on the page?
12. iNaturalist: may the site link the `lauratamayo` observations, and are their locations obscured?

## Sources used in the draft

- Facebook page: https://www.facebook.com/AlertaChirimacha/ (colors, the WhatsApp number, the example alert of April 13, 2026, the cover photo, the slogan).
- Alerta Chirimacha report log (the team's Google Sheet, not in this repository), October 2020 to November 2026.
- iNaturalist observations, account `lauratamayo`, linked for comparing photos: https://www.inaturalist.org/observations?subview=grid&user_id=lauratamayo&verifiable=any
- The team's video (CHAGAS_Final_v2, 2022) and its four parts.
- Tamayo LD, Condori-Pino CE, Sanchez Z, Gonçalves R, Málaga Chávez FS, Castillo-Neyra R, Levy MZ, Paz-Soldan VA. *PLOS Neglected Tropical Diseases* 17(10), 2023. https://doaj.org/article/b79d628a9df244229518f3d67ce0c716 (first 26 months: 206 reports, 11 *T. infestans*; 57% more confirmed reports than the traditional system).
- Texas A&M Kissing Bug Community Science Program, "Found a bug?": https://kissingbug.tamu.edu/found-a-bug/ (handling, closed container, notes to record, squashed insects, identification traits). Its statement that no other insects carry the parasite was **not** copied: the lab showed in the laboratory that bed bugs can transmit *T. cruzi* (Salazar R, Castillo-Neyra R, Tustin AW, Borrini-Mayorí K, Náquira C, Levy MZ. *Am J Trop Med Hyg* 92(2):331–335, 2015. doi:10.4269/ajtmh.14-0483).
- CDC triatomine guidance (don't touch or squash the bug; capture it in a container): https://www.cdc.gov/parasites/chagas/gen_info/vectors
- Map: INEI via perugeopkg (CC BY-SA 4.0), OpenStreetMap contributors (ODbL), Terrain Tiles on AWS Open Data. Details in `site/data/map/README.md`.
