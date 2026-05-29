"""
LOST.guide - Tower Data-to-AI pipeline.

Wraps the Nimble trademark knockout agent (nimble_knockout.py) as a Tower app:
  acquire (live web via Nimble) -> structure (risk-scored conflicts) -> land in
  an Apache Iceberg lakehouse table managed by Tower.

Runs on Tower's serverless compute; also runs locally and falls back to local
Parquet when no Tower catalog is available, so it can be tested without an account.

Build target: DeveloperWeek New York 2026 - Tower "Pipeline Challenge: Data-to-AI".
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import uuid

import pyarrow as pa


def _load_secret(name: str, default: str = "") -> str:
    """Pull a secret from Tower when running on Tower, else from the environment."""
    try:
        import tower
        v = tower.secret(name, default=default)
        if v:
            return v
    except Exception:
        pass
    return os.environ.get(name, default)


# The Nimble client initializes at import time from NIMBLE_API_KEY, so make sure
# the key is in the environment BEFORE importing the knockout module.
if not os.environ.get("NIMBLE_API_KEY"):
    _k = _load_secret("NIMBLE_API_KEY")
    if _k:
        os.environ["NIMBLE_API_KEY"] = _k

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nimble_knockout as nk  # noqa: E402  (import after key is set)


def _param(name: str, default):
    """Read a Tower parameter when on Tower, else an env var, else the default."""
    try:
        import tower
        v = tower.param(name, default=default)
        if v not in (None, ""):
            return v
    except Exception:
        pass
    return os.environ.get(name, default)


RUNS_SCHEMA = pa.schema([
    pa.field("run_id", pa.string()),
    pa.field("searched_at", pa.string()),
    pa.field("mark", pa.string()),
    pa.field("classes", pa.string()),
    pa.field("niche", pa.string()),
    pa.field("sources", pa.string()),
    pa.field("n_conflicts", pa.int64()),
    pa.field("risk_score", pa.string()),
    pa.field("recommendation", pa.string()),
    pa.field("stub", pa.bool_()),
    pa.field("nimble_calls", pa.int64()),
])

CONFLICTS_SCHEMA = pa.schema([
    pa.field("run_id", pa.string()),
    pa.field("mark", pa.string()),
    pa.field("source", pa.string()),
    pa.field("conflict_mark", pa.string()),
    pa.field("holder", pa.string()),
    pa.field("similarity", pa.float64()),
    pa.field("risk", pa.string()),
    pa.field("url", pa.string()),
])


def _runs_table(report, run_id: str) -> pa.Table:
    return pa.table({
        "run_id": [run_id],
        "searched_at": [report.searched_at],
        "mark": [report.mark],
        "classes": [",".join(str(c) for c in report.classes)],
        "niche": [report.niche],
        "sources": [",".join(report.sources_searched)],
        "n_conflicts": [len(report.conflicts)],
        "risk_score": [report.risk_score],
        "recommendation": [report.recommendation],
        "stub": [report.stub],
        "nimble_calls": [report.nimble_calls_made],
    }, schema=RUNS_SCHEMA)


def _conflicts_table(report, run_id: str) -> pa.Table:
    rows = report.conflicts
    return pa.table({
        "run_id": [run_id] * len(rows),
        "mark": [report.mark] * len(rows),
        "source": [c.source for c in rows],
        "conflict_mark": [c.mark for c in rows],
        "holder": [c.holder for c in rows],
        "similarity": [float(c.similarity) for c in rows],
        "risk": [c.risk for c in rows],
        "url": [c.url for c in rows],
    }, schema=CONFLICTS_SCHEMA)


def _write_tower(name: str, schema: pa.Schema, data: pa.Table, namespace: str) -> None:
    import tower
    t = tower.tables(name, namespace=namespace).create_if_not_exists(schema)
    if data.num_rows:
        t.insert(data)


def _write_local(name: str, data: pa.Table, outdir: str) -> str:
    import pyarrow.parquet as pq
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, name + ".parquet")
    pq.write_table(data, path)
    return path


def main() -> None:
    mark = _param("mark", "BANKSY AI")
    classes = [int(x) for x in str(_param("classes", "9,42,41")).split(",") if str(x).strip()]
    niche = _param("niche", "mobile-app")
    namespace = _param("namespace", "lostguide")

    report = nk.knockout_search(mark, classes, niche)
    run_id = uuid.uuid4().hex
    runs = _runs_table(report, run_id)
    conflicts = _conflicts_table(report, run_id)

    sink = "tower-iceberg"
    try:
        _write_tower("knockout_runs", RUNS_SCHEMA, runs, namespace)
        _write_tower("knockout_conflicts", CONFLICTS_SCHEMA, conflicts, namespace)
    except Exception as e:
        sink = "local-parquet"
        outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out")
        p1 = _write_local("knockout_runs", runs, outdir)
        p2 = _write_local("knockout_conflicts", conflicts, outdir)
        sys.stderr.write(
            f"[tower] lakehouse unavailable ({type(e).__name__}: {e}); wrote local Parquet:\n"
            f"  {p1}\n  {p2}\n"
        )

    print(json.dumps({
        "run_id": run_id,
        "mark": mark,
        "classes": classes,
        "niche": niche,
        "stub": report.stub,
        "nimble_calls": report.nimble_calls_made,
        "n_conflicts": len(report.conflicts),
        "risk_score": report.risk_score,
        "recommendation": report.recommendation,
        "sink": sink,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }, indent=2))


if __name__ == "__main__":
    main()
