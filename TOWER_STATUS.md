# Tower deployment status — honest record (updated 2026-05-30, GREEN)

## TL;DR
- **Local pipeline: WORKS** — `python pipeline.py` runs live (6 Nimble calls, ~27–29 conflicts,
  HIGH → DO_NOT_PROCEED).
- **Tower deploy: WORKS** — app `lostguide-knockout` healthy/active (v5).
- **Tower cloud run: WORKS (GREEN)** — Run #7 `exited` cleanly (`tower apps show` → `exited 1`):
  `stub:false, nimble_calls:6, n_conflicts:27, risk:HIGH, DO_NOT_PROCEED, sink:local-parquet`.

## What was actually wrong (and the fix)
Runs #1–#6 all **errored in 1–3s right after "spinning up pod,"** before any code ran.
A no-dependency `print("hello")` control app failed identically — proving it was **not** our
code, requirements.txt, or Towerfile. Root cause: the `banksi-ai` account had **no compute
runner** to execute pods.

**Fix:** attach a self-hosted Tower runner via Docker on the project machine:
```powershell
docker pull towerhq/tower-runner:latest
docker run -d --name tower-runner --restart unless-stopped -e TOWER_API_KEY=<sk-...> towerhq/tower-runner:latest
```
Runner registered with the Tower control plane ("runner online, waiting for work"); the very
next `tower run` went green (Run #7, `exited`).

## Operating notes
- The runner must be **running** (the container, or Docker Desktop on Windows) for cloud runs
  to execute. `docker ps` should show `tower-runner` Up; `docker logs tower-runner` shows activity.
- `sink: local-parquet` means no Iceberg catalog is configured. Enable Tower's managed Iceberg
  Catalog in the web console (slug `default`) to persist `knockout_runs` / `knockout_conflicts`;
  no code or redeploy needed.
- **Security:** the `TOWER_API_KEY` used here was shared in a chat session — rotate it in the
  Tower console (Settings → API keys → regenerate) and update the runner's env.

## Run history (tower apps show, 2026-05-30)
`run_results: exited 1, errored 6` — runs #1–#6 errored (no runner); **#7 exited (runner attached).**
