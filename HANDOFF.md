# Handoff: Alerta Chirimacha website

Read this first in any new task on this project. Written 2026-11-23. Prepared by Sil Necesito (volunteer research assistant) for Dr. Michael Z. Levy and the Alerta Chirimacha team.

> This repository is shared with the team. Commit messages, pull requests and notes here are written for the team. Keep them professional: no personal notes.

## 1. What this project is

Alerta Chirimacha is the lab's community reporting system for chirimachas in Arequipa: residents send photos of suspected insects by WhatsApp, the team identifies them, and confirmed findings lead to neighborhood alerts on Facebook. In the Nov 18 planning meeting the team made the Alerta Chirimacha website the **priority project**, ahead of the lab homepage.

Related repository: `SILvennxaenecesito/levy-lab-website` (lab homepage drafts and the "Immune System for the City" explainer).

| Deliverable | Path | Status |
|---|---|---|
| Site plan | `PLAN.md` | Draft v1 for team review |
| One-page site, Spanish first with English toggle | `site/index.html` (built from `site/source/`) | Draft v1, sample data on the map |

## 2. Requirements and decisions

**From the Nov 18 planning meeting**
- People now find Alerta Chirimacha mainly by searching online, so a real website is needed. It should be a website, not an app.
- Main page for people reporting ("reporta tu chirimacha"), plus "see our reports" as a map.
- **Decision:** reporting links to the WhatsApp number instead of a web form.
- **Decision:** reports are mapped at the district level, not by locality.
- Open: map from district counts, the lab's own georeferencing, or an embedded iNaturalist map.
- Keep the Facebook page's color scheme; adapt its content.
- Use the team's existing Spanish videos (a 4-minute full version plus shorter clips). No new videos.
- About 95% of reported insects are not chirimachas. The look-alike gallery idea was dropped.
- Keep text short.
- Later: Alerta Chirimacha might run in Texas when the Texas project starts.

**From the Nov 4 meeting:** no self-identification needed; district-level data only, never household locations or names.

## 3. Content rules

1. **No fabricated data.** Sample numbers stay labeled "DATOS DE EJEMPLO / SAMPLE DATA" until the team's counts replace them.
2. **Privacy:** only totals per district. No addresses, names, phone numbers of reporters, coordinates or photo metadata.
3. Keep the **draft banner** until the team approves the site.
4. **No logos** (Penn, UPCH, Gerencia Regional de Salud, or the Alerta Chirimacha mark) until the team confirms which may be used. Partner names stay marked *por confirmar*.
5. The only contact channels are the program's WhatsApp number (989 279 579, to be confirmed) and the Facebook page https://www.facebook.com/AlertaChirimacha/. This differs from the lab-site drafts, which carry no phone numbers; for this site the team chose WhatsApp.
6. Spanish first, English toggle. Short sentences.
7. Health and safety wording (handling insects, bites) stays marked *por confirmar* until the team approves it. The current wording follows CDC triatomine guidance.
8. No new videos or photos generated; use the team's own material, with credit.

## 4. How the site is built

- `site/source/template.html`: edit this, not `index.html`. Bilingual macros are Spanish first: `⟦Español||English⟧` in HTML, `⟪Español||English⟫` in SVG text, `attr="⟦…||…⟧"` for attributes, and `<title>/<desc>/<option>⟦…||…⟧`. Note: the lab-site repo uses English first.
- `site/source/build.py`: reads `site/data/`, checks that the district names match and that no two share a map cell, draws the hexagon map and the table, and expands the macros. Run from `site/source/`: `python3 build.py template.html ../data ../index.html`.
- Language: Spanish by default; the choice is remembered in the browser; `?lang=en` or `#en` opens English.
- No external requests except Google Fonts. Text falls back to system fonts.

## 5. Verified facts used on the page

- Tamayo LD, Condori-Pino CE, Sanchez Z, Gonçalves R, Málaga Chávez FS, Castillo-Neyra R, Levy MZ, Paz-Soldan VA. *PLOS NTD* 17(10), 2023. https://doaj.org/article/b79d628a9df244229518f3d67ce0c716. First 26 months: 206 reports, 11 (5.3%) confirmed *T. infestans*, no *T. cruzi* found; 57% more confirmed reports than the traditional system; 10% more infested houses than active and passive surveillance combined.
- CDC (triatomine bug FAQs): don't touch or squash a suspected triatomine; place a container over it and slide it inside. https://www.cdc.gov/parasites/chagas/gen_info/vectors
- Arequipa province has 29 districts. The ubigeo codes in `districts.csv` follow INEI's numbering (040101–040129); only the first five were checked against a published list, so check the rest before joining data.
- Example alert (Facebook, April 13, 2026): Loma Verde, Santa Martha and Ampliación Pampas del Cusco, Jacobo Hunter district.

## 6. Open items

**Waiting on the team**
- [ ] Confirm the WhatsApp number and the wording of "what happens next".
- [ ] Spanish videos (full version and clips).
- [ ] District counts (reports, and confirmed, if they will be shown).
- [ ] Access to the Alerta Chirimacha Google Drive photo archive; decide which photos can be shown.
- [ ] Partner names and logos; bite advice wording.
- [ ] Map option (A/B/C in PLAN.md) and hosting.
- [ ] Earlier images: the email or Google Doc with the initial images is being looked for.

**Next drafting steps**
- [ ] Replace the sample counts once `site/data/reports-by-district.csv` arrives.
- [ ] Embed the videos (a lightweight player that does not load until tapped).
- [ ] Optional: real district boundaries (INEI/geoBoundaries, with attribution) instead of the schematic hexagons.
- [ ] Spanish review by native speakers; test on low-end Android phones.

## 7. Change log

**2026-11-23**: Repository started. Added PLAN.md, HANDOFF.md, README.md, and draft v1 of the site: report-by-WhatsApp hero, three steps, short facts, a district hexagon map with sample data, an alert example, video slots, FAQ, an about section, and an English toggle.
