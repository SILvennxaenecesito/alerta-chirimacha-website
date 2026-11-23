# Alerta Chirimacha website: plan

Draft v1, November 2026, for review by the Alerta Chirimacha team. Everything here is a proposal; the open questions at the end need the team's answers before launch.

## Why a website

- People now find Alerta Chirimacha by searching online, more than through flyers or Facebook ads. A real website lets them find the reporting number quickly (Nov 18 planning meeting).
- A website, not an app: residents rarely download apps (limited phone storage, slow internet, and many single-disease apps already).

## Who it is for

1. **Residents of Arequipa who found an insect** (main audience). Spanish speakers on phones, sometimes with slow connections. They need one thing: how to report, right away.
2. **People curious about results.** A simple district-level view of reports.
3. **Partners and researchers.** A short "about" section and a link to the published study.

## Decisions so far (Nov 18 planning meeting)

- Reporting links to the **WhatsApp number**, not a web form. People want to know that someone will answer.
- Reports are mapped at the **district level**. Most reports only record district and province, and aggregating protects the people who report.
- The site uses the **color scheme of the Facebook page**, and its content is adapted from the Facebook page.
- The team's existing **Spanish videos** go on the page (one full video, about 4 minutes, plus shorter clips). No new videos are made.
- **Short text.** Other reporting sites were judged to carry too much information.
- The idea of a gallery of look-alike insects was dropped: people don't look closely at bugs.

## Site map

One page, Spanish first, with an English toggle. On phones, a "Reportar por WhatsApp" bar stays at the bottom once the visitor scrolls past the first button.

| # | Section | What it does |
|---|---|---|
| 1 | Report (top) | "¿Encontraste una chirimacha?", the WhatsApp button and the number in large type. "Free · No app needed · We never publish names or addresses." |
| 2 | How to report | Three steps: don't touch or squash it (trap it in a jar or bag), take a photo, send it with your district. Then what happens next, and a reminder that most reports are not chirimachas (11 of the first 206). |
| 3 | What is the chirimacha | Three short facts: nocturnal blood feeder; hides in wall cracks and animal pens; wingless young are chirimachas too. |
| 4 | Reports by district | Map of the 29 districts of Arequipa province. Tap a district to see its numbers. Privacy note. Table view for accessibility. |
| 5 | Alerts | How neighborhood alerts work, the latest alert, and a link to all alerts on Facebook. |
| 6 | Videos | The team's Spanish videos. |
| 7 | FAQ | Cost, apps, privacy, what if it isn't a chirimacha, what to do after a bite. |
| 8 | About | What Alerta Chirimacha is, who runs it, and a link to the 2023 study. Footer with the slogan, WhatsApp and Facebook. |

## Data and privacy

- The site shows **only totals per district**: never homes, addresses, names or phone numbers.
- Counts live in one file, `site/data/reports-by-district.csv` (columns `district, reports, confirmed`). The team updates it and rebuilds the page. Until that file exists, the build uses made-up sample numbers and labels them "DATOS DE EJEMPLO" on the map, the panel and the table.
- **Photos (later).** Following the meeting, only photos of reported insects that are not dangerous. Before publishing: remove location metadata (EXIF/GPS) and crop out anything that could identify a home.
- Whether to show **confirmed chirimachas per district** publicly is an open question; the draft leaves that value as "to be decided".

## The map: three options (open question)

| Option | Pros | Cons |
|---|---|---|
| **A. Our own district map from the lab's counts** (the draft uses a schematic hexagon layout; it can move to real district boundaries from INEI or geoBoundaries, with attribution) | Full control over privacy; light and fast; matches the site's design; works on slow phones | The team has to update the counts file |
| B. The lab's own georeferences, aggregated to districts | Most accurate | Same work as A plus geocoding; very few reports have localities |
| C. Embed the iNaturalist map | Already exists; iNaturalist obscures exact locations | Depends on iNaturalist permissions; mixes in non-chirimacha observations; heavier page; outside our design |

**Suggestion:** A, with a link to the iNaturalist observations for anyone who wants more.

## How it is built

- One self-contained HTML file (about 60 KB): no server, no database, no tracking. It loads quickly on slow connections.
- Source: `site/source/template.html` (bilingual text as `⟦Español||English⟧`) and `site/source/build.py`, which draws the district map from `site/data/` and builds `site/index.html`.
- Hosting options are the same as for the lab site: GitHub Pages, a Penn alias, or a domain the lab owns. This is not decided yet. At launch: remove the draft banner and the `noindex` tag, and add the site's address to the Facebook page.

## Phases

1. **Draft v1 (this pull request):** structure, Spanish and English copy, sample map.
2. **Content from the team:** confirm the WhatsApp number, partner names, what happens after a report, and the bite advice; send the videos, photos and district counts.
3. **Real data and review:** real counts and map, Spanish review by native speakers, test on low-end Android phones.
4. **Launch:** hosting decision; remove the draft banner after approval; link from the Facebook page.
5. **Later:** a Texas version if Alerta Chirimacha starts there.

## Open questions for the team

1. Is **989 279 579** the right WhatsApp number to publish?
2. What happens after a report is confirmed? The draft says: "we arrange an inspection of your home and alert your neighbors" (marked *por confirmar*).
3. Show confirmed chirimachas per district, or only total reports?
4. Show the full list of neighborhood alerts on the site, or only link to Facebook?
5. Which partner names (and logos, if any) can appear? The draft names Universidad Peruana Cayetano Heredia, the University of Pennsylvania and the Gerencia Regional de Salud de Arequipa, marked *por confirmar*. It shows no logos.
6. Wording for the bite question in the FAQ.
7. Which photos can be shown, with what credit?
8. Map option A, B or C?
9. Hosting and domain.

## Sources used in the draft

- Facebook page: https://www.facebook.com/AlertaChirimacha/ (colors, the WhatsApp number, the example alert of April 13, 2026, the slogan).
- Tamayo LD, Condori-Pino CE, Sanchez Z, Gonçalves R, Málaga Chávez FS, Castillo-Neyra R, Levy MZ, Paz-Soldan VA. *PLOS Neglected Tropical Diseases* 17(10), 2023. https://doaj.org/article/b79d628a9df244229518f3d67ce0c716 (first 26 months: 206 reports, 11 *T. infestans*; 57% more confirmed reports than the traditional system).
- Safety advice follows CDC's triatomine guidance (don't touch or squash the bug; capture it in a container): https://www.cdc.gov/parasites/chagas/gen_info/vectors
- The 29 districts of Arequipa province. Their INEI ubigeo codes (040101–040129) are in `site/data/districts.csv`; check them before joining the lab's data.
