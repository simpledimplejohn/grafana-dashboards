# grafana-dashboards

Dashboards built on the home stack, synced to the work stack through this repo.

| Dashboard | uid | Data source |
|---|---|---|
| [Spooky Host Metrics](dashboards/windows-host-spooky.json) | `windows-host-spooky` | Prometheus (windows_exporter) |

`title-cards/` holds the HTML source of each themed title card (already embedded in the dashboard JSON).

## Importing at work

Grafana → **Dashboards → New → Import** → upload the JSON → pick a folder → Import.
Re-importing the same file overwrites the dashboard, since it has the same uid.

The data source is a `datasource` variable, so the dashboard uses whatever Prometheus data source exists there.

The animated title cards need this in `grafana.ini`, or the card shows as raw HTML:

```ini
[panels]
disable_sanitize_html = true
```

## Dashboard standards

Every dashboard has a `datasource` variable, a `host` variable that every query filters on, an
environment variable when one exists, and an HTML title card (full width, short) at the top above the first row.
