# LOST.guide Knockout — Tower Data-to-AI Pipeline

Wraps the Nimble trademark **knockout** agent as a Tower app: **acquire** live web data
(Nimble across USPTO TESS, App Store, Google Play, GitHub, Product Hunt, web) → **structure**
into risk-scored conflicts → **land** in an Apache Iceberg lakehouse managed by Tower.

Built for the DeveloperWeek New York 2026 **"Pipeline Challenge: Data-to-AI."**

## Files
- `pipeline.py` — Tower entrypoint. Reads params (`mark`, `classes`, `niche`, `namespace`),
  runs the knockout via `nimble_knockout.py`, writes two Iceberg tables: `knockout_runs`
  (one row per run) and `knockout_conflicts` (one row per conflict). Falls back to local
  Parquet if no Tower catalog/session is available, so it runs locally without an account.
- `nimble_knockout.py` — the live-web knockout agent (reused, not forked).
- `Towerfile` — app + parameter definitions.
- `requirements.txt` — `nimble-python`, `pyarrow` (the Tower runner provides `tower` and its Iceberg deps, so do **not** list `tower` in requirements.txt — that breaks the runner build).

## Deploy (needs a tower.dev account)
```bash
pip install "tower[iceberg]"     # CLI + SDK + Iceberg deps (pyiceberg, polars). The [iceberg] extra is REQUIRED for the lakehouse.
tower version                     # confirm install — note: `version`, NOT `--version`
tower login
tower secrets create --name=NIMBLE_API_KEY --value=<your key>
tower apps create --name=lostguide-knockout
tower deploy                      # run from this directory (it has the Towerfile)
tower run --parameter=mark="BANKSY AI" --parameter=classes="9,42,41"
```
If `tower` is "not recognized" after a `--user` install, its Scripts dir isn't on PATH — add it
(`%APPDATA%\Python\Python3xx\Scripts` on Windows) or call `tower.exe` by full path.

Enable Tower's managed **Iceberg Catalog** in the web UI so a `default` catalog exists; confirm
with `tower catalogs list` (the CLI lists/shows catalogs but does not create them). Without it,
runs still succeed and fall back to local Parquet.

## Schedule (optional)
```bash
tower schedules create --app=lostguide-knockout --cron "0 9 * * 1" --parameter=mark="BANKSY AI" --parameter=classes="9,42,41"
tower schedules list
```

## Local test (no account)
```bash
pip install "tower[iceberg]" nimble-python
export NIMBLE_API_KEY=<your key>     # live mode (omit -> stub mode)
python pipeline.py                    # writes ./_out/*.parquet and prints a JSON summary
```

## Data-to-AI mapping (the challenge brief)
| Challenge ask | This pipeline |
|---|---|
| Acquire data from web APIs | Nimble live search across 6 sources |
| Store in a lakehouse | Iceberg `knockout_runs` + `knockout_conflicts` |
| Feature engineering | similarity + source-weighted risk grading |
| Launch AI agents for interpretation | the knockout agent's PROCEED / DO_NOT_PROCEED verdict |
| Orchestrate / schedule | `tower run` on demand or `tower schedules` |

_No secrets are stored in this repo; the Nimble key is read from the environment / Tower secrets at runtime._
