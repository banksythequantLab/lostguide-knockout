# LOST.guide - Trademark Knockout Agent + Tower Pipeline

An AI agent that **sees the live web** to clear trademarks before you file - built for the
**DeveloperWeek New York 2026 Hackathon** (Nimble + Tower challenges). Part of **LOST.guide**
(Lawyer Outlined Self-help Tutorials), an attorney-built front door to U.S. legal forms.

A trademark filing fee is non-refundable, and the conflicts that sink an application often are
not in the government register - they are live on the App Store, Google Play, GitHub, and
Product Hunt. This agent uses **Nimble** to search those live sources, scores each hit for name
similarity and class overlap, and returns an attorney-style verdict
(`PROCEED` / `PROCEED_WITH_AMENDMENT` / `DO_NOT_PROCEED`).

## What is here
| File | What it is |
|---|---|
| `nimble_knockout.py` | The agent: multi-source live-web knockout search via Nimble, risk scoring, attorney-style narrative. CLI + importable. |
| `pipeline.py` | Tower Data-to-AI pipeline: acquire (Nimble) -> feature-engineer -> land in an Iceberg lakehouse (`knockout_runs`, `knockout_conflicts`). |
| `Towerfile` | Tower app + parameter definitions. |
| `requirements.txt` | `nimble-python`, `pyarrow`. |
| `README_TOWER.md` | Tower deploy guide. |

## Run the agent (CLI)
```bash
pip install nimble-python
export NIMBLE_API_KEY=<your Nimble key>   # omit to run in offline demo/stub mode
python nimble_knockout.py --mark "BANKSY AI" --classes 9,42,41 --niche mobile-app
```
Verified live (2026-05-29): "BANKSY AI" -> 6 Nimble calls across USPTO TESS, App Store, Google
Play, GitHub, Product Hunt, and web -> 25 conflicts -> **HIGH / DO_NOT_PROCEED**. A nonsense
control mark returns 0 conflicts -> **PROCEED**.

## Run as a Tower pipeline
See [README_TOWER.md](./README_TOWER.md). In short:
```bash
pip install tower pyarrow
tower login
tower secrets create --name=NIMBLE_API_KEY --value=<your key>
tower deploy && tower run
```

## Hackathon challenges
- **Nimble - "Build an Agentic App That Sees the Live Web":** an autonomous trademark-clearance research workflow over real-time web data.
- **Tower - "Pipeline Challenge: Data-to-AI":** acquire web data -> Iceberg lakehouse -> feature engineering -> AI-agent interpretation.

_No secrets are stored in this repo; the Nimble key is read from the environment / Tower secrets at runtime._
