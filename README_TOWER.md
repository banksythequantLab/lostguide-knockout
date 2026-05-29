# LOST.guide Knockout — Tower Data-to-AI Pipeline

Wraps the Nimble trademark **knockout** agent as a Tower app:
**acquire** live web data (Nimble across USPTO TESS, App Store, Google Play,
GitHub, Product Hunt, web) → **structure** it into risk-scored conflicts →
**land** it in an Apache Iceberg lakehouse table managed by Tower.

Built for the DeveloperWeek New York 2026 **"Pipeline Challenge: Data-to-AI."**

## Files
- `pipeline.py` — Tower entrypoint. Reads params (`mark`, `classes`, `niche`,
  `namespace`), runs the knockout via `nimble_knockout.py`, and writes two
  Iceberg tables: `knockout_runs` (one row per run) and `knockout_conflicts`
  (one row per conflict). Falls back to local Parquet if no Tower catalog is
  available, so it runs locally without an account.
- `nimble_knockout.py` — the existing live-web knockout agent (reused, not forked).
- `Towerfile` — app + parameter definitions.
- `requirements.txt` — runtime dependencies (`nimble-python`, `pyarrow`).

## Status (honest)
- ✅ Pipeline logic, Iceberg schemas, and the Nimble acquisition step are **built
  and run locally** — verified producing real conflict rows to Parquet.
- ⏳ **Deploying to Tower needs the tower.dev account** (login + secret + deploy);
  see steps below. Until then the lakehouse write is exercised through the
  local-Parquet fallback path (identical data, same code path).

## Deploy (needs your tower.dev account)
```bash
pip install tower                                   # Tower CLI + SDK
tower login
tower secrets create --name=NIMBLE_API_KEY --value=<your key>   # never hardcode
tower apps create --name=lostguide-knockout
tower deploy                                        # run from this directory
tower run --parameter=mark='BANKSY AI' --parameter=classes='9,42,41'
```
Schedule recurring clearances from the Tower UI or CLI — a mark that is clear
today may not be next month, so re-running on a schedule keeps the lakehouse current.

## Local test (no account needed)
```bash
set NIMBLE_API_KEY=<your key>     # Windows; enables live mode (omit -> stub mode)
python pipeline.py                # writes ./_out/*.parquet and prints a JSON summary
```

## Data-to-AI mapping (the challenge brief)
| Challenge ask | This pipeline |
|---|---|
| Acquire data from web APIs | Nimble live search across 6 sources |
| Store in a lakehouse | Iceberg `knockout_runs` + `knockout_conflicts` |
| Feature engineering | similarity + source-weighted risk grading |
| Launch AI agents for interpretation | the knockout agent's PROCEED / DO_NOT_PROCEED verdict |
| Orchestrate / schedule | `tower run` on demand or scheduled |
