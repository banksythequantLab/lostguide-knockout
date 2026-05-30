# Tower deployment status — honest record (2026-05-30)

## TL;DR
- **Local pipeline: WORKS** — `python pipeline.py` runs live (6 Nimble calls, ~27–29 conflicts,
  HIGH → DO_NOT_PROCEED) and writes `knockout_runs` + `knockout_conflicts` (Parquet locally).
- **Tower deploy: WORKS** — app `lostguide-knockout` healthy/active (v5).
- **Tower cloud run: FAILS** — all 7 runs `errored` 1–3s after "spinning up pod," before any
  code runs (`tower apps show` → `exited 0, errored 7`). **No successful hosted run exists.**

## Why it fails
A no-dependency `print("hello")` control app fails identically, so it is **not** our code,
requirements.txt, or Towerfile. The `banksi-ai` account has **no compute runner** attached to
execute pods, so every pod dies at startup.

## Attempt to fix (did NOT succeed in this environment)
Tried to attach a self-hosted runner two ways on the project machine (Vesper):
1. **Docker** (`docker run … towerhq/tower-runner`): **Docker Desktop would not start** — the
   `docker-desktop` WSL distro stayed `Stopped` and the daemon pipe never came up, so every
   docker command failed. Runner never launched.
2. **Native Windows binary** (`tower-runner.exe` 0.8.17): it is a **Windows Service** and must be
   registered via `install-service.ps1` **as Administrator** (then `Start-Service TowerRunner`).
   Running the exe directly fails with `Service dispatcher failed (code 1063)`. Not installed
   here because it needs elevation + persistent service install (owner approval required).

## What will actually make it green (one of these)
- **Start Docker Desktop**, then:
  `docker run -d --name tower-runner --restart unless-stopped -e TOWER_API_KEY=<sk-...> towerhq/tower-runner:latest`
  then `tower run` → should `exited` clean. Verify: `docker logs tower-runner` shows "online".
- **OR install the native service (Admin):** from `B:\tower-runner`, `./install-service.ps1`,
  set the key in `%ProgramData%\tower-runner\tower-runner.env`, `Start-Service TowerRunner`.
- Then enable an Iceberg catalog in the Tower console if you want `sink: tower-iceberg`
  instead of `local-parquet`.

## For the hackathon submission
Claim the **local verification** only (real + reproducible). Do **NOT** claim a hosted Tower
run — `tower apps show lostguide-knockout` must read `exited >= 1` before that's true.

## Security
The `TOWER_API_KEY` was shared in a chat session — **rotate it** (Tower console → API keys →
regenerate) and update wherever the runner reads it.

## Run history (tower apps show, 2026-05-30)
`run_results: exited 0, errored 7` — runs #1–#7 all `errored` (no runner attached).
