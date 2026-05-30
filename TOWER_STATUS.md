# Tower deployment status — honest record (GREEN, 2026-05-30)

## TL;DR
- **Local pipeline: WORKS** — `python pipeline.py` runs live (6 Nimble calls, ~27 conflicts,
  HIGH → DO_NOT_PROCEED).
- **Tower deploy: WORKS** — app `lostguide-knockout` healthy/active (v5).
- **Tower cloud run: WORKS (GREEN)** — Run **#8 `exited`** cleanly. Verified two ways:
  1. `tower apps show` → `run_results: exited 1, errored 7`
  2. Run #8 log JSON: `stub:false, nimble_calls:6, n_conflicts:27, risk_score:HIGH,
     recommendation:DO_NOT_PROCEED, sink:local-parquet`

## What was wrong, and the fix
Runs #1–#7 all **errored 1–3s after "spinning up pod,"** before any code ran. A no-dependency
`print("hello")` control app failed identically — proving it was **not** our code. Root cause:
the `banksi-ai` account had **no compute runner** to execute pods.

**Fix — attach a self-hosted Tower runner via Docker on the project machine (Vesper):**
```powershell
docker pull towerhq/tower-runner:latest
docker run -d --name tower-runner --restart unless-stopped -e TOWER_API_KEY=<sk-...> towerhq/tower-runner:latest
docker logs tower-runner      # -> "runner registered; awaiting work"
```
The runner registered with the Tower control plane; the next `tower run` (#8) executed and
`exited` cleanly. (Earlier attempts failed only because Docker Desktop wasn't started yet —
once the daemon was up, the pull + run worked.)

## Operating notes
- The runner container must be **Up** for cloud runs to execute (`docker ps` shows
  `tower-runner`; `--restart unless-stopped` brings it back after reboot once Docker is running).
- `sink: local-parquet` means the run wrote Parquet **inside the runner container** because no
  Iceberg catalog is configured. To persist to a managed lakehouse (`knockout_runs` /
  `knockout_conflicts`), enable Tower's Iceberg Catalog in the web console (slug `default`) —
  no code change or redeploy needed; `sink` then reads `tower-iceberg`.

## Security — ACTION NEEDED
The `TOWER_API_KEY` was shared in a chat session. **Rotate it** (Tower console → API keys →
regenerate), then update the runner:
`docker rm -f tower-runner; docker run -d --name tower-runner --restart unless-stopped -e TOWER_API_KEY=<new-key> towerhq/tower-runner:latest`

## Run history (tower apps show, 2026-05-30)
`run_results: exited 1, errored 7` — #1–#7 errored (no runner); **#8 exited (Docker runner attached).**
