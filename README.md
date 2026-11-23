# Alerta Chirimacha website

Draft website for Alerta Chirimacha, the community surveillance system for chirimachas (*Triatoma infestans*) in Arequipa, Peru. Residents report an insect by WhatsApp; the site also shows reports by district.

Everything here is a **draft for the team's review**, not the official site yet.

- **Plan:** [PLAN.md](PLAN.md): audience, decisions, site map, privacy, map options, open questions.
- **Context for anyone picking up the work:** [HANDOFF.md](HANDOFF.md).

## View the draft

Open `site/index.html` in a browser. It is one self-contained file. Spanish is the default; the EN button (or `?lang=en` / `#en` at the end of the address) switches to English.

## Folders

- `site/index.html`: the built page. Don't edit it by hand.
- `site/source/template.html`: the page source. Bilingual text is written as `⟦Español||English⟧` (Spanish first), or `⟪Español||English⟫` inside SVG text.
- `site/source/build.py`: draws the district map and builds `site/index.html`.
- `site/data/districts.csv`: the 29 districts of Arequipa province and their place on the hexagon map.
- `site/data/reports-by-district.sample.csv`: **made-up** counts used until real data arrives.

## Rebuild

From `site/source/`:

```
python3 build.py template.html ../data ../index.html
```

## Add the real report counts

1. Create `site/data/reports-by-district.csv` with the columns `district,reports,confirmed`, using exactly the district names in `districts.csv` (leave `confirmed` empty if it should not be shown).
2. Rebuild. When this file exists, the build uses it instead of the sample file, and the "DATOS DE EJEMPLO / SAMPLE DATA" labels disappear.

Only totals per district go in this file: never addresses, names, phone numbers or coordinates.
