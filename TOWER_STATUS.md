# Tower deployment status — honest record (2026-05-30)

## TL;DR
- **Local pipeline: WORKS.** `python pipeline.py` runs the agent live (6 Nimble calls,
  ~28 conflicts, HIGH → DO_NOT_PROCEED) and writes `knockout_runs` + `knockout_conflicts`
  (Parquet locally; Iceberg when a catalog is configured).
- **Tower deploy: WORKS.** `tower deploy` succeeds; app `lostguide-knockout` is healthy/active (v5).
- **Tower cloud RUN: FAILS.** Every cloud run (5/5, plus a control test) **errors 1–3s after
  "spinning up pod," before any code executes.** This is an infra/runner issue, not our code.

## How we know it's not our code
A throwaway control app — a single `print("hello from tower cloud")` with **no dependencies,
no Iceberg, no Nimble** — was deployed and run on Tower and **failed identically** ("had an
error" right after pod dispatch). If a one-line print can't run, the problem is the runner
environment, not `pipeline.py`.

## Most likely cause
The account `banksi-ai` is a **personal team**. Tower's model uses **runners** to execute
cloud runs (their docs lead with self-hosted runner installation, and the session token
carries a `runners` scope). The symptom — instant failure at pod startup with no logs —
matches **no runner being available/attached** to execute the pod. The Tower CLI does not
expose a `runners` subcommand, and `apps logs` only shows the dispatch line, so the precise
runner error is only visible in the Tower **web console**.

## What to check / try (needs the Tower web UI or support)
1. Open a failed run and read the system/runner error:
   `https://app.tower.dev/banksi-ai/default/apps/lostguide-knockout/runs/5`
2. In the console, check **Runners / Compute**: is a cloud runner provisioned for this
   account tier, or must a **self-hosted runner** be attached? (Self-hosted install:
   `docker run … towerhq/tower-runner:latest` with `TOWER_API_KEY`, or the Windows MSI.)
3. If hackathon credits/entitlements grant managed compute, confirm they're active on
   `banksi-ai`; contact Tower if pod startup keeps failing with no runner.

## For the hackathon submission
Claim the **local verification** (it's real and reproducible): live multi-source Nimble
acquisition → risk-scored conflicts → lakehouse-schema'd tables, deploy-ready on Tower.
Do **not** claim a successful hosted Tower run until one actually shows `exited` in
`tower apps show lostguide-knockout`.

## Run history (from `tower apps show`, 2026-05-30)
`run_results: errored 5, exited 0` — runs #1–#5 all `errored`, elapsed 1–3s each.
