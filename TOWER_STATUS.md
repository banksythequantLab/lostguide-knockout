# Tower deployment status — honest record (2026-05-30, final for this session)

## TL;DR (updated 2026-05-30 — Tower LOCAL execution now verified green)
- **Tower LOCAL run: WORKS ✅** — `tower run --local` (driven via the Tower MCP `tower_run_local`
  tool, and via CLI) executes the real pipeline through Tower's runtime: Tower installs deps
  (pyarrow, nimble-python), runs LIVE (stub=false, 6 Nimble calls, 28 conflicts,
  HIGH → DO_NOT_PROCEED), and exits cleanly. **Must run from a LOCAL drive (E:), not the B:\ UNC
  share** — see root cause below.
- **Plain `python pipeline.py`: WORKS** — same live result.
- **Tower deploy: WORKS** — app healthy/active (now v6).
- **Tower CLOUD run: STILL FAILS** — runs error at pod spin-up (`exit_code: null`, ~1s);
  `exited 0, errored 12`. Deploying from a local drive (E:) did NOT fix it → confirmed server-side.

## Root causes (both isolated 2026-05-30)
1. **Local "SpawnFailed" was the B:\ UNC drive.** `USERPROFILE=B:\` (\\Johnson\b network share);
   Tower's local runtime stages/spawns from the profile, which fails over UNC. Running the app
   from a **local drive (E:\lostguide-knockout)** via the MCP → local run succeeds cleanly.
2. **Cloud pod-spawn failure is separate and server-side.** Reproduced from both B: and E: drives,
   and with a zero-dependency `print()` app — pods die in ~1s before code runs. Not quota
   (beta plan = 1000 compute min, used seconds), not entitlement, not our code. Only Tower can fix.
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

**Credits/quota ruled out (checked via `GET /v1/plan`):** the account is on a `beta` plan with
**1000 compute minutes**, 20 app slots, 20 schedules, 5 members, and 1 self-hosted-runner
entitlement (i.e. Team-tier, granted free). Runs die in ~1s, so consumed minutes are negligible —
**this is NOT a billing/credits problem, and cloud compute IS entitled.** (`GET /v1/usage` is 403
for this token's scope, so the exact consumed counter isn't readable, but exhaustion is
implausible at ~1s/run against 1000 min.) execution_region = `eu-central-1`.

Conclusion: cloud pods **fail to spawn** (~1s, `exit_code: null`) despite available quota and a
healthy self-hosted runner that never receives work. This is a **Tower platform/runtime issue**
(pod spin-up), only Tower can resolve — see `TOWER_SUPPORT_EMAIL.md`.

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
