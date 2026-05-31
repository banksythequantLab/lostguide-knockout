# Tower support email — ready to send

**To:** support@tower.dev (and/or the DWNY 2026 / Tower hackathon contact)
**From:** Derek Soltis — Tower account `banksi-ai` (personal team)
**Subject:** Hackathon app: deploy works, self-hosted runner healthy, but all runs error in ~1s (never routed to my runner)

---

Hi Tower team,

I'm building a Data-to-AI pipeline (`lostguide-knockout`) for the DeveloperWeek New York 2026
hackathon and I'm stuck on cloud runs. Deploys succeed, but **every run errors in ~1 second**
before my code executes, and I've ruled out my app as the cause. I'd appreciate help getting a
run to actually execute.

**Account / app**
- Org/team: `banksi-ai` (personal), execution_region: `eu-central-1`
- Plan (`GET /v1/plan`): `beta` — 1000 compute minutes, 20 app slots, 20 schedules,
  5 members, 1 self-hosted-runner entitlement. **So this is NOT a quota/credit problem:**
  I have 1000 compute minutes and have consumed only seconds (every run dies in ~1s).
- App: `lostguide-knockout` (currently v5), environments tried: `default` and `production`

**Symptom**
- `tower deploy` → success. `tower run` → "Run #N scheduled," then the run status becomes
  `errored` after ~1–2s. Run log only ever shows:
  `dispatched to runner 019e6540-… , spinning up pod` — then it errors. No application output.
- `tower apps show lostguide-knockout` → `run_results: exited 0, errored 11`.

**What I've already verified (so it's not my code)**
- **Minimal repro on my account:** app `hello-tower` — entire code is one line,
  `print("hello from tower - contact confirmed")`, no dependencies. Deployed clean (v1), but
  Run #1 ERRORED. Run log shows only `[setup] dispatched to runner 019e6540-d5d9-7c6e-…,
  spinning up pod`, then it errors (`run_results: exited 0, errored 1`). The code never runs.
  This app is still on my account if you want to inspect it.
- Same failure on both `--environment=default` and `--environment=production`.
- `requirements.txt` and `Towerfile` are minimal and valid; **`tower run --local` runs the full
  pipeline LIVE through Tower's runtime** — venv provisioned, deps installed, `NIMBLE_API_KEY`
  pulled from my Tower secret store, real work done, "exited cleanly." So the app, deps, secret,
  and Towerfile are all good; only the **cloud** run fails.

**Self-hosted runner (registered, healthy, but never used)**
- I attached a self-hosted runner via Docker: `towerhq/tower-runner:latest` (v0.11.4), key via
  `TOWER_API_KEY`. It connects and registers:
  `Registered with control plane, runner_id=019e7a01-62b8-75c0-8cc4-66f0b10a5288`
  `Using local subprocess backend`
- `GET /v1/runners` shows it `status: healthy`, recent `last_health_check_at`,
  `max_concurrent_apps: 1`, but **`num_runs: 0`** and **`active_runs: 0`** — it never receives work.
- Every run instead dispatches to a cloud-pool runner (`019e6540-…`), which is what errors.

**My questions**
1. My `beta` plan shows 1000 compute minutes available (I've used only seconds), so this isn't a
   quota issue — yet every cloud pod dies in ~1s at spin-up with `exit_code: null`. Is there a
   platform problem starting pods for my account in region `eu-central-1`? What's the actual
   pod-spawn error on your side?
2. How do I route runs to my **self-hosted** runner (`019e7a01-…`)? I don't see a `--runner`
   flag on `tower run` or a Runners tab in the console — is there an environment→runner binding
   I need to set?
3. Is there a way to see the underlying pod/system error for an errored run? The CLI
   `apps logs` only shows the "spinning up pod" line.

Thanks very much — happy to share any IDs or logs you need.

Derek Soltis
