# Tower deployment status — honest record (2026-05-30)

## TL;DR
- **Local pipeline: WORKS** — `python pipeline.py` runs live (6 Nimble calls, ~27 conflicts,
  HIGH → DO_NOT_PROCEED).
- **Tower deploy: WORKS** — app `lostguide-knockout` healthy/active (v5).
- **Self-hosted runner: registered** — Docker container `tower-runner` is Up and registered with
  the Tower control plane (runner_id `019e7a01-…`, "Using local subprocess backend").
- **Tower cloud run: STILL FAILING** — all 8 runs `errored` (`tower apps show` → `exited 0, errored 8`).
  **No successful hosted run exists.**

## Open problem (why the runner didn't help)
Run #8 was dispatched to runner `019e6540-…` — a DIFFERENT id than the self-hosted runner we just
registered (`019e7a01-…`). The run is being routed to Tower's managed/cloud runner pool, not our
new local runner, and it still errors 1–3s after "spinning up pod." So registering a runner was
necessary progress but did not change run routing on this account.

## Likely next checks (need the Tower web console)
- Confirm in the console whether the self-hosted runner appears and is "online/idle."
- Check if runs must be explicitly targeted to a self-hosted runner (an environment/runner-pool
  setting), or whether the account is pinned to a cloud runner pool that has no capacity.
- Read the per-run system error at the run link (CLI `apps logs` only shows the dispatch line).

## For the hackathon submission
Claim the **local verification** only. Do NOT claim a hosted Tower run — `tower apps show
lostguide-knockout` must read `exited >= 1` before that is true. Current: `exited 0, errored 8`.

## Security — ACTION NEEDED
The `TOWER_API_KEY` was shared in a chat session. Rotate it (Tower console → API keys →
regenerate) and restart the runner container with the new key.

## Run history (tower apps show, 2026-05-30)
`run_results: exited 0, errored 8` — runs #1–#8 all errored. Self-hosted runner registered but
runs not routed to it.
