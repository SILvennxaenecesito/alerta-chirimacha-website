# Map layers

GeoJSON files (WGS84) that `site/source/mapdraw.py` turns into the two map views (city and province). They were made once with `tools/prepare_map_layers.py`; re-run it only to refresh the base map.

| File | What | Source and licence |
|---|---|---|
| `districts.geojson` | The 29 districts of Arequipa province, simplified to about 6 m. Each district has its INEI ubigeo code, `anchor` (where its report circle goes: the middle of its built-up area) and `label_pt` (visual centre, used for districts with no built-up area). | INEI district boundaries, from [perugeopkg](https://github.com/PaulESantos/perugeopkg) (`geo/prov_arequipa_arequipa.gpkg`) by Paul E. Santos Andrade. **CC BY-SA 4.0**: credit INEI and perugeopkg, and share changes to these boundary files under the same licence. |
| `province.geojson` | Outline of the province (outer edges of the districts). | Same as above, CC BY-SA 4.0. |
| `context.geojson` | Main roads, rivers, lakes, the built-up area, the volcanoes El Misti, Chachani and Pichu Pichu, and the Plaza de Armas. Simplified. | © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), **ODbL 1.0**, via [OpenFreeMap](https://openfreemap.org) vector tiles and Nominatim. The built-up area is drawn from street density and land use, so its edges are approximate. |
| `terrain.geojson` | Areas above 2000, 3000, 4000 and 5000 m (province) and 2300 to 5000 m (city). | [Terrain Tiles on AWS Open Data](https://registry.opendata.aws/terrain-tiles/) (SRTM and other sources), contoured and simplified. |

The page credits all four under the map and in the footer. Keep those credits if the map is reused.

## Refreshing

1. Download `geo/prov_arequipa_arequipa.gpkg` from perugeopkg (or INEI's own district layer).
2. Run `tools/map-layers-browser.js` in a browser (instructions at the top of that file). It saves `osm_layers.txt`.
3. From the repository root:

   ```
   python3 tools/prepare_map_layers.py --gpkg prov_arequipa_arequipa.gpkg --osm osm_layers.txt --out site/data/map
   ```

   This needs numpy, matplotlib and scipy. The site build itself needs only Python.
4. Rebuild the page (see the README).

No report data is stored here, only the base map.
