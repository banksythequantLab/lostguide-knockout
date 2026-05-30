# Tower deployment status — honest record (2026-05-30, final for this session)

## TL;DR
- **Local pipeline: WORKS** — `python pipeline.py` runs live (6 Nimble calls, ~27 conflicts,
  HIGH → DO_NOT_PROCEED).
- **Tower deploy: WORKS** — app `lostguide-knockout` healthy/active (v5).
- **Self-hosted runner: REGISTERED & HEALTHY** — Tower's own API confirms it
  (`GET /v1/runners` → `status: healthy`, recent `last_health_check_at`, `max_concurrent_apps: 1`).
- **Tower cloud run: STILL FAILS** — 11/11 runs `errored` (`tower apps show` → `exited 0, errored 11`).
  **No successful hosted run exists.**

## Root cause (now evidence-backed, not a guess)
Every run is dispatched to a **Tower cloud-pool runner** (id prefix `019e6540-…`) and dies in
~1 second with **no application output** (the pod never executes `pipeline.py`). Meanwhile our
**self-hosted runner** (`019e7a01-…` / re-registered `019e7a62-…`) stays `healthy` per the Tower
API but its `num_runs` never leaves **0** and `active_runs` is always **0** — i.e. Tower never
routes work to it.

Proven by:
- A zero-dependency `print("hello")` control app fails identically → not our code/deps/Towerfile.
- Tried `--environment=default` and `--environment=production` → both error the same way.
- Restarted / re-pulled the runner; Tower API still shows it healthy with `num_runs: 0`.
- `tower run` has **no `--runner` flag**, and the web console has **no Runners tab**, so run→runner
  routing cannot be set from the CLI by us.

Conclusion: the account (`banksi-ai`, personal team) either has **no working cloud compute
entitlement** and/or **is not configured to route runs to the self-hosted runner**. This is an
account/platform setting only **Tower** can change — see `TOWER_SUPPORT_EMAIL.md`.

## To get a green run later (any one of these)
1. Tower enables cloud compute on the account, OR binds the `default`/`production` environment to
   the self-hosted runner (support request).
2. If a console control appears (Runners/Compute settings), point the environment at runner
   `019e7a01-…` and re-run.
3. Keep the Docker runner Up:
   `docker run -d --name tower-runner --restart unless-stopped -e TOWER_API_KEY=<key> towerhq/tower-runner:latest`
   then `tower run` — verify success with `tower apps show lostguide-knockout` reading `exited >= 1`.

## For the hackathon submission
Claim the **local verification** only (real + reproducible). Do NOT claim a hosted Tower run —
current truth is `exited 0, errored 11`.

## Security — ACTION NEEDED
The `TOWER_API_KEY` was shared in a chat session. Rotate it (Tower console → API keys →
regenerate) and restart the runner container with the new key.

## Additional finding — `tower run --local` also fails (2026-05-30)
Tower's own skill doc recommends `tower run --local` for development (runs locally WITH Tower
secret access). Tried it: fails with **`platform error: SpawnFailed — App crashed during local
execution`** — Tower's local runtime can't spawn on this machine either. So ALL THREE Tower
execution paths fail (cloud runner, self-hosted runner, local), while plain `python pipeline.py`
runs perfectly. The blocker is Tower's runtime layer, not our app.

## Tower MCP — checked (28 tools, no runner control)
`tower mcp-server` exposes 28 tools (apps/deploy/run_local/run_remote/file/secrets/schedules/
catalogs/teams). There is **no runner tool or runner-target parameter** anywhere — so runner
routing cannot be set by any client. `tower_catalogs_list` returns empty (no Iceberg catalog on
the account), which is why the sink falls back to local Parquet.

## Run history (tower apps show, 2026-05-30)
`run_results: exited 0, errored 11` — runs #1–#11 all errored; self-hosted runner healthy but
received 0 of them.
