# robotocore coverage dashboard

Auto-updating dashboard tracking [robotocore](https://github.com/robotocore/robotocore)'s AWS API coverage and parity against botocore.

## What it shows

- **Parity Report** — searchable, filterable list of all 157 AWS services with operation-level implementation status
- **Coverage Treemap** — visual map of service coverage, sized by operation count, colored by implementation percentage

## Run locally

```bash
# Generate fresh data (requires uv and git)
python scripts/extract-data.py

# Serve the dashboard
cd site && python -m http.server
```

Open http://localhost:8000

## How it works

A daily GitHub Action clones the robotocore repo, runs its parity report generator, transforms the output into `data/coverage.json`, and commits the result. GitHub Pages serves the static site from the `site/` directory.

## Links

- [robotocore](https://github.com/robotocore/robotocore)
