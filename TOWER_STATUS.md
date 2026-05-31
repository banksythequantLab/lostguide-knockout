# Tower deployment status — honest record (2026-05-30, final for this session)

## TL;DR
- **Local pipeline: WORKS** — `python pipeline.py` runs live (6 Nimble calls, ~27 conflicts,
  HIGH → DO_NOT_PROCEED).
- **Tower deploy: WORKS** — app `lostguide-knockout` healthy/active (v5).
- **Tower CLOUD run: FAILS** — all runs error at pod spin-up (`exit_code: null`, ~1s);
  `exited 0, errored 11`.
- **Tower `--local`, minimal new app: WORKS ✅** — a from-scratch one-line `print()` app
  (`name="twr-test"`, NOT deployed) ran via `tower run --local` from D:\twr_test: venv created,
  printed its line, "Success! Your local run exited cleanly." Earlier `SpawnFailed` was specific to
  the **B:\ UNC drive**; local drives are clean.
- **Tower `--local`, the FULL pipeline: WORKS ✅ GREEN + LIVE (verified 2026-05-31)** — run from a
  local drive with a Towerfile app name that is NOT a deployed app (e.g. `lostguide-local`), and
  with `tower` in requirements.txt so the venv has the SDK. Exact log (shell env cleared, so the
  key came from the Tower secret store): `[pipeline] tower_sdk=True key_source=tower-secret
  key_present=True` then `stub: false, nimble_calls: 6, n_conflicts: 27-28, HIGH, DO_NOT_PROCEED,
  Success! Your local run exited cleanly.` Reproduced twice from the canonical repo files.
  Two gotchas that made earlier attempts fail: (a) a DEPLOYED app name makes `--local` refuse with
  "Running apps by name locally is not supported yet" — use a non-deployed name; (b) without
  `tower` in requirements.txt, `tower.secret()` can't run in the venv and it falls back to stub.
  (See TOWER_LOCAL_RUN_PROOF.txt for the exact stdout.)
- **Tower MCP `tower_run_local`/`tower_file_*` via stdio:** returned no response in scripted
  probes (likely needs a longer-lived server handshake than a one-shot pipe). The MCP exposes the
  same 28 ops as the CLI; no runner-selection tool exists.
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
