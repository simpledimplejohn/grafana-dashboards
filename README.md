# grafana-dashboards

Dashboards built on the home stack, synced to the work stack through this repo.

| Dashboard | uid | Data source |
|---|---|---|
| [Spooky Host Metrics](dashboards/windows-host-spooky.json) | `windows-host-spooky` | Prometheus (windows_exporter) |

`title-cards/` holds the source of each themed title card. The built card is already embedded in the
dashboard JSON, so importing the dashboard is all you need.

## Importing at work

Grafana → **Dashboards → New → Import** → upload the JSON → pick a folder → Import.
Re-importing the same file overwrites the dashboard, since it has the same uid.

The data source is a `datasource` variable, so the dashboard uses whatever Prometheus data source exists there.

No Grafana config changes are needed: the cards work with HTML sanitizing **on** (the default).

## Title cards (sanitizer-safe)

Grafana's sanitizer strips `<style>`, `<svg>`, `<script>`, font links and CSS like `position`,
`transform`, `opacity` and `animation` from text panels. It keeps layout/colour inline styles
(`display:flex`, `gap`, `padding`, `margin`, `border`, `border-radius`, shadows, backgrounds; longhand
`flex-grow`/`flex-shrink`/`flex-basis`, not the `flex` shorthand) and `data:image/svg+xml` images.

So each card is:

- **HTML with allowed inline styles** for layout and anything with `${variables}` (Grafana doesn't
  interpolate inside images)
- **SVG images** for everything animated or needing a web font. SVGs run their own `<style>`,
  `@keyframes` and SMIL animations, and fonts are embedded as base64 (SIL OFL fonts from Google Fonts)
- **an overlay SVG** placed on top with `margin-left:-100%` for things that fly over the text

Build a card into its dashboard JSON (and optionally save it to Grafana):

```
python title-cards/build_cards.py spooky
python title-cards/build_cards.py spooky --push
```

## Dashboard standards

Every dashboard has a `datasource` variable, a `host` variable that every query filters on, an
environment variable when one exists, and an HTML title card (full width, short) at the top above the first row.
