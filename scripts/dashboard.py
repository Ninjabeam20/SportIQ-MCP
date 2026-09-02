"""Local analytics dashboard for sportiq-mcp.

Read-only. Pulls the longest window each source still has, archives a snapshot
under ``analytics-archive/``, renders ``dashboard.html``. Run::

    uv sync --extra dev --extra analytics
    bash scripts/pull_home_analytics.sh   # Dell JSONL
    uv run python scripts/dashboard.py

Live telemetry is Dell JSONL (``SPORTIQ_ANALYTICS_JSONL``). GCP Cloud Logging /
Monitoring collectors fail after project ``sportiq-mcp-prod`` was shut down
(2026-09-02) and fall back to ``.dashboard_cache/``. GitHub + PyPI still live.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import webbrowser
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

GCP_PROJECT = "sportiq-mcp-prod"
CLOUD_RUN_SERVICE = "sportiq-mcp"
CLOUD_RUN_REGION = "us-central1"
GITHUB_REPO = "Ninjabeam20/SportIQ-MCP"
PYPI_PACKAGE = "sportiq-mcp"
SERVICE_START = datetime(2026, 6, 9, tzinfo=UTC)
LOGGING_RETENTION_DAYS = 30
LOG_SCAN_CAP = 200_000

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".dashboard_cache"
ARCHIVE_DIR = REPO_ROOT / "analytics-archive"
TEMPLATE = Path(__file__).resolve().parent / "dashboard_template.html"
OUTPUT_HTML = REPO_ROOT / "dashboard.html"

_UA_RULES: list[tuple[str, str]] = [
    ("claude", "Claude"),
    ("anthropic", "Claude"),
    ("chatgpt", "ChatGPT"),
    ("openai", "ChatGPT"),
    ("cursor", "Cursor"),
    ("cline", "Cline"),
    ("windsurf", "Windsurf"),
    ("vscode", "VS Code"),
    ("modelcontextprotocol", "MCP inspector"),
    ("mcp-remote", "mcp-remote"),
    ("node", "Node client"),
    ("python-httpx", "python-httpx"),
    ("httpx", "python-httpx"),
    ("python-urllib", "python-urllib"),
    ("python-requests", "python-requests"),
    ("go-http", "Go client"),
    ("curl/", "curl"),
    ("google-cloud-scheduler", "Cloud Scheduler"),
    ("googlehc", "GCP healthcheck"),
    ("kube-probe", "GCP healthcheck"),
]


def classify_user_agent(ua: str) -> str:
    if not ua:
        return "unknown"
    low = ua.lower()
    for needle, label in _UA_RULES:
        if needle in low:
            return label
    return "other"


def _token_from_dotenv(path: Path) -> str | None:
    """Read GITHUB_TOKEN / GH_TOKEN from a dotenv file. Never logs the value."""
    if not path.is_file():
        return None
    try:
        for line in path.read_text().splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            if raw.startswith("export "):
                raw = raw[7:].strip()
            key, _, val = raw.partition("=")
            if key in ("GITHUB_TOKEN", "GH_TOKEN") and val:
                return val.strip().strip("'\"")
    except OSError:
        return None
    return None


def _github_token() -> str | None:
    # Prefer process env, then repo .env (has read:user). `gh auth token` is last
    # because the CLI login is often gist/read:org/repo and cannot list Sponsors.
    tok = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if tok:
        return tok
    tok = _token_from_dotenv(REPO_ROOT / ".env")
    if tok:
        return tok
    try:
        out = subprocess.check_output(
            ["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL, timeout=8
        ).strip()
        return out or None
    except Exception:
        return None


def _sport_of(tool: str) -> str:
    if tool.startswith("football_"):
        return "football"
    if tool.startswith("f1_"):
        return "f1"
    if tool.startswith("cricket_"):
        return "cricket"
    if tool.startswith("cross_"):
        return "cross-sport"
    if tool.startswith("sportiq_"):
        return "health"
    return "other"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round((pct / 100.0) * (len(ordered) - 1)))
    return round(ordered[idx], 1)


def _day(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# Cache helpers
# --------------------------------------------------------------------------- #
def _cache_write(name: str, payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    payload["_cached_at"] = datetime.now(UTC).isoformat()
    (CACHE_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, default=str))


def _cache_read(name: str) -> dict[str, Any]:
    path = CACHE_DIR / f"{name}.json"
    if path.exists():
        data = json.loads(path.read_text())
        data["_from_cache"] = True
        return data
    return {"_unavailable": True}


def _cache_age_hours(name: str) -> float | None:
    path = CACHE_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        cached_at = datetime.fromisoformat(data["_cached_at"])
        return (datetime.now(UTC) - cached_at).total_seconds() / 3600
    except Exception:
        return None


def _collect(name: str, fn, max_cache_hours: float = 0) -> dict[str, Any]:
    if max_cache_hours > 0:
        age = _cache_age_hours(name)
        if age is not None and age < max_cache_hours:
            cached = _cache_read(name)
            cached["_from_cache"] = True
            return cached
    try:
        result = fn()
        _cache_write(name, result)
        result["_from_cache"] = False
        return result
    except Exception as exc:
        cached = _cache_read(name)
        cached["_error"] = f"{type(exc).__name__}: {exc}"
        return cached


def _strip_private(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop underscore event dumps before embedding in HTML."""
    out: dict[str, Any] = {}
    for k, v in payload.items():
        if k.startswith("_events"):
            continue
        if isinstance(v, dict):
            out[k] = {ik: iv for ik, iv in v.items() if not ik.startswith("_events")}
        else:
            out[k] = v
    return out


# --------------------------------------------------------------------------- #
# Monitoring helpers
# --------------------------------------------------------------------------- #
def _mon_interval(start: datetime, end: datetime):
    from google.cloud import monitoring_v3

    return monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": int(end.timestamp())},
            "start_time": {"seconds": int(start.timestamp())},
        }
    )


def _mon_daily(
    client: Any,
    metric_type: str,
    aligner: str,
    reducer: str,
    interval: Any,
    group_by: list[str] | None = None,
) -> list[Any]:
    from google.cloud import monitoring_v3

    agg: dict[str, Any] = {
        "alignment_period": {"seconds": 86400},
        "per_series_aligner": getattr(monitoring_v3.Aggregation.Aligner, aligner),
        "cross_series_reducer": getattr(monitoring_v3.Aggregation.Reducer, reducer),
    }
    if group_by:
        agg["group_by_fields"] = group_by
    return list(
        client.list_time_series(
            request={
                "name": f"projects/{GCP_PROJECT}",
                "filter": (
                    f'metric.type="{metric_type}" '
                    f'resource.labels.service_name="{CLOUD_RUN_SERVICE}" '
                    f'resource.labels.location="{CLOUD_RUN_REGION}"'
                ),
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": monitoring_v3.Aggregation(agg),
            }
        )
    )


def _point_num(point: Any) -> float:
    if point.value.int64_value:
        return float(point.value.int64_value)
    return float(point.value.double_value or 0.0)


def _series_to_day_map(series_list: list[Any], label_key: str | None = None) -> dict:
    out: dict[str, Any] = {}
    for series in series_list:
        label = series.metric.labels.get(label_key, "other") if label_key else None
        for point in series.points:
            day = datetime.fromtimestamp(point.interval.end_time.timestamp(), tz=UTC).strftime(
                "%Y-%m-%d"
            )
            val = _point_num(point)
            if label_key:
                bucket = out.setdefault(day, {})
                bucket[label] = bucket.get(label, 0) + val
            else:
                out[day] = val
    return out


# --------------------------------------------------------------------------- #
# Collector 1 — Cloud Run (Cloud Monitoring, full retained history)
# --------------------------------------------------------------------------- #
def collect_cloud_run() -> dict[str, Any]:
    from google.cloud import monitoring_v3 as monitoring

    client = monitoring.MetricServiceClient()
    now = datetime.now(UTC)
    interval = _mon_interval(SERVICE_START, now)

    counts_by_day = _series_to_day_map(
        _mon_daily(
            client,
            "run.googleapis.com/request_count",
            "ALIGN_SUM",
            "REDUCE_SUM",
            interval,
            ["metric.labels.response_code_class"],
        ),
        "response_code_class",
    )
    # ints for the stacked bar
    counts_by_day = {d: {k: int(v) for k, v in codes.items()} for d, codes in counts_by_day.items()}

    codes_by_day = _series_to_day_map(
        _mon_daily(
            client,
            "run.googleapis.com/request_count",
            "ALIGN_SUM",
            "REDUCE_SUM",
            interval,
            ["metric.labels.response_code"],
        ),
        "response_code",
    )
    codes_by_day = {d: {k: int(v) for k, v in codes.items()} for d, codes in codes_by_day.items()}
    code_totals: dict[str, int] = {}
    for codes in codes_by_day.values():
        for code, n in codes.items():
            code_totals[code] = code_totals.get(code, 0) + n

    def _latency(percentile: int) -> dict[str, float]:
        aligner = "ALIGN_PERCENTILE_50" if percentile == 50 else "ALIGN_PERCENTILE_99"
        raw = _series_to_day_map(
            _mon_daily(
                client,
                "run.googleapis.com/request_latencies",
                aligner,
                "REDUCE_MEAN",
                interval,
            )
        )
        return {d: round(v, 1) for d, v in raw.items()}

    extras: dict[str, dict[str, float]] = {}
    extra_specs = [
        ("instance_max", "run.googleapis.com/container/instance_count", "ALIGN_MAX", "REDUCE_MAX"),
        (
            "billable_s",
            "run.googleapis.com/container/billable_instance_time",
            "ALIGN_SUM",
            "REDUCE_SUM",
        ),
        (
            "cpu_p99",
            "run.googleapis.com/container/cpu/utilizations",
            "ALIGN_PERCENTILE_99",
            "REDUCE_MEAN",
        ),
        (
            "mem_p99",
            "run.googleapis.com/container/memory/utilizations",
            "ALIGN_PERCENTILE_99",
            "REDUCE_MEAN",
        ),
        (
            "startup_p99_ms",
            "run.googleapis.com/container/startup_latencies",
            "ALIGN_PERCENTILE_99",
            "REDUCE_MEAN",
        ),
    ]
    for name, metric, align, reduce in extra_specs:
        try:
            extras[name] = {
                d: round(v, 4)
                for d, v in _series_to_day_map(
                    _mon_daily(client, metric, align, reduce, interval)
                ).items()
            }
        except Exception:
            extras[name] = {}

    days = sorted(counts_by_day.keys())
    total = sum(sum(v.values()) for v in counts_by_day.values())
    class_totals: dict[str, int] = {}
    for day_counts in counts_by_day.values():
        for klass, n in day_counts.items():
            class_totals[klass] = class_totals.get(klass, 0) + n
    last_30 = [d for d in days if d >= (now - timedelta(days=30)).strftime("%Y-%m-%d")]
    total_30 = sum(sum(counts_by_day[d].values()) for d in last_30)
    billable_s = sum(extras.get("billable_s", {}).values())

    return {
        "window": "all_available",
        "source": "Cloud Monitoring",
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "days": days,
        "counts_by_day": counts_by_day,
        "codes_by_day": codes_by_day,
        "code_totals": dict(sorted(code_totals.items(), key=lambda kv: -kv[1])),
        "class_totals": class_totals,
        "p50": _latency(50),
        "p99": _latency(99),
        "instance_max": extras.get("instance_max", {}),
        "billable_s": extras.get("billable_s", {}),
        "cpu_p99": extras.get("cpu_p99", {}),
        "mem_p99": extras.get("mem_p99", {}),
        "startup_p99_ms": extras.get("startup_p99_ms", {}),
        "total_requests": total,
        "total_requests_30d": total_30,
        "billable_hours": round(billable_s / 3600.0, 2),
        "pct_4xx": round(100 * class_totals.get("4xx", 0) / total, 1) if total else 0,
        "pct_2xx": round(100 * class_totals.get("2xx", 0) / total, 1) if total else 0,
        "pct_5xx": round(100 * class_totals.get("5xx", 0) / total, 1) if total else 0,
    }


# --------------------------------------------------------------------------- #
# Collector 2 — HTTP + mcp_request logs (Logging, 30d retention)
# --------------------------------------------------------------------------- #
def collect_http_logs() -> dict[str, Any]:
    from google.cloud import logging_v2

    client = logging_v2.Client(project=GCP_PROJECT)
    since_dt = datetime.now(UTC) - timedelta(days=LOGGING_RETENTION_DAYS)
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    log_filter = (
        'resource.type="cloud_run_revision" '
        f'resource.labels.service_name="{CLOUD_RUN_SERVICE}" '
        f'timestamp>="{since}" '
        '(jsonPayload.event="mcp_request" OR httpRequest.requestUrl:"/mcp")'
    )

    ua_buckets: dict[str, int] = {}
    client_buckets: dict[str, int] = {}
    methods: dict[str, int] = {}
    statuses: dict[str, int] = {}
    revisions: dict[str, int] = {}
    by_hour: dict[str, int] = {f"{h:02d}": 0 for h in range(24)}
    by_dow: dict[str, int] = {d: 0 for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
    by_day: dict[str, int] = {}
    source = "user_agent"
    sampled = 0
    truncated = False
    events: list[dict[str, Any]] = []
    first_ts: datetime | None = None
    last_ts: datetime | None = None

    for i, entry in enumerate(client.list_entries(filter_=log_filter, page_size=1000)):
        if i >= LOG_SCAN_CAP:
            truncated = True
            break
        sampled += 1
        ts = getattr(entry, "timestamp", None)
        if isinstance(ts, datetime):
            ts = ts.astimezone(UTC) if ts.tzinfo else ts.replace(tzinfo=UTC)
            first_ts = ts if first_ts is None or ts < first_ts else first_ts
            last_ts = ts if last_ts is None or ts > last_ts else last_ts
            by_hour[ts.strftime("%H")] = by_hour.get(ts.strftime("%H"), 0) + 1
            by_dow[ts.strftime("%a")] += 1
            by_day[_day(ts)] = by_day.get(_day(ts), 0) + 1

        labels = getattr(getattr(entry, "resource", None), "labels", None) or {}
        rev = ""
        if hasattr(labels, "get") or isinstance(labels, dict):
            rev = labels.get("revision_name") or ""
        if rev:
            revisions[rev] = revisions.get(rev, 0) + 1

        payload = getattr(entry, "payload", None)
        client_name = None
        ua = ""
        if isinstance(payload, dict) and payload.get("event") == "mcp_request":
            client_name = payload.get("client_name") or None
            ua = payload.get("user_agent") or ""
            if client_name:
                source = "client_info"
                client_buckets[client_name] = client_buckets.get(client_name, 0) + 1
            else:
                label = classify_user_agent(ua)
                client_buckets[label] = client_buckets.get(label, 0) + 1
        else:
            http = getattr(entry, "http_request", None) or {}
            if isinstance(http, dict):
                ua = http.get("userAgent", "") or ""
                method = http.get("requestMethod") or http.get("request_method") or "?"
                status = str(http.get("status") or "")
            else:
                ua = getattr(http, "user_agent", "") or ""
                method = getattr(http, "request_method", None) or "?"
                status = str(getattr(http, "status", "") or "")
            methods[method] = methods.get(method, 0) + 1
            if status:
                statuses[status] = statuses.get(status, 0) + 1
            label = classify_user_agent(ua)
            client_buckets[label] = client_buckets.get(label, 0) + 1

        ua_label = classify_user_agent(ua)
        ua_buckets[ua_label] = ua_buckets.get(ua_label, 0) + 1
        events.append(
            {
                "ts": ts.isoformat() if isinstance(ts, datetime) else None,
                "client": client_name or ua_label,
                "ua": ua_label,
                "rev": rev or None,
            }
        )

    return {
        "window": f"{LOGGING_RETENTION_DAYS}d",
        "source": "Cloud Logging",
        "first_ts": first_ts.isoformat() if first_ts else None,
        "last_ts": last_ts.isoformat() if last_ts else None,
        "sampled": sampled,
        "truncated": truncated,
        "buckets": ua_buckets,
        "client_buckets": client_buckets,
        "methods": methods,
        "statuses": dict(sorted(statuses.items(), key=lambda kv: -kv[1])),
        "revisions": dict(sorted(revisions.items(), key=lambda kv: -kv[1])),
        "by_hour": by_hour,
        "by_dow": by_dow,
        "by_day": dict(sorted(by_day.items())),
        "source_kind": source,
        "_events": events,
    }


# --------------------------------------------------------------------------- #
# Collector 3 — tool_call events (Logging, 30d)
# --------------------------------------------------------------------------- #
def collect_tool_stats() -> dict[str, Any]:
    from google.cloud import logging_v2

    client = logging_v2.Client(project=GCP_PROJECT)
    since_dt = datetime.now(UTC) - timedelta(days=LOGGING_RETENTION_DAYS)
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    log_filter = (
        'resource.type="cloud_run_revision" '
        f'resource.labels.service_name="{CLOUD_RUN_SERVICE}" '
        f'timestamp>="{since}" '
        'jsonPayload.event="tool_call"'
    )

    per_tool: dict[str, dict[str, Any]] = {}
    per_client: dict[str, int] = {}
    matrix: dict[str, dict[str, int]] = {}
    error_codes: dict[str, int] = {}
    by_day: dict[str, dict[str, int]] = {}
    by_sport: dict[str, dict[str, int]] = {}
    by_source: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    by_hour: dict[str, int] = {f"{h:02d}": 0 for h in range(24)}
    by_dow: dict[str, int] = {d: 0 for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
    total_ok = total_err = 0
    truncated = False
    events: list[dict[str, Any]] = []
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    latencies: list[float] = []

    for i, entry in enumerate(client.list_entries(filter_=log_filter, page_size=1000)):
        if i >= LOG_SCAN_CAP:
            truncated = True
            break
        p = getattr(entry, "payload", None)
        if not isinstance(p, dict):
            continue
        tool = p.get("tool") or "unknown"
        success = bool(p.get("success"))
        latency = p.get("latency_ms")
        label = p.get("client_name") or classify_user_agent(p.get("user_agent") or "")
        source = p.get("source") or "unknown"
        outcome = p.get("outcome") or ("ok" if success else "error")
        sport = _sport_of(tool)

        t = per_tool.setdefault(tool, {"calls": 0, "errors": 0, "lat": []})
        t["calls"] += 1
        if isinstance(latency, (int, float)):
            t["lat"].append(float(latency))
            latencies.append(float(latency))
        per_client[label] = per_client.get(label, 0) + 1
        matrix.setdefault(label, {})
        matrix[label][tool] = matrix[label].get(tool, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        sp = by_sport.setdefault(sport, {"ok": 0, "error": 0})

        ts = getattr(entry, "timestamp", None)
        if isinstance(ts, datetime):
            ts = ts.astimezone(UTC) if ts.tzinfo else ts.replace(tzinfo=UTC)
            first_ts = ts if first_ts is None or ts < first_ts else first_ts
            last_ts = ts if last_ts is None or ts > last_ts else last_ts
            by_hour[ts.strftime("%H")] += 1
            by_dow[ts.strftime("%a")] += 1
            day = _day(ts)
        else:
            day = "unknown"
        d = by_day.setdefault(day, {"ok": 0, "error": 0})
        if success:
            total_ok += 1
            d["ok"] += 1
            sp["ok"] += 1
        else:
            t["errors"] += 1
            total_err += 1
            d["error"] += 1
            sp["error"] += 1
            code = p.get("error") or outcome
            error_codes[str(code)] = error_codes.get(str(code), 0) + 1

        events.append(
            {
                "ts": ts.isoformat() if isinstance(ts, datetime) else None,
                "tool": tool,
                "success": success,
                "outcome": outcome,
                "source": source,
                "latency_ms": latency if isinstance(latency, (int, float)) else None,
                "client": label,
                "sport": sport,
            }
        )

    tools = []
    for name, t in per_tool.items():
        calls = t["calls"]
        lat = t["lat"]
        tools.append(
            {
                "tool": name,
                "sport": _sport_of(name),
                "calls": calls,
                "errors": t["errors"],
                "error_rate": round(t["errors"] / calls, 4) if calls else 0,
                "avg_ms": round(sum(lat) / len(lat), 1) if lat else 0,
                "p50_ms": _percentile(lat, 50),
                "p99_ms": _percentile(lat, 99),
            }
        )
    tools.sort(key=lambda r: r["calls"], reverse=True)
    days = sorted(d for d in by_day if d != "unknown")
    total = total_ok + total_err

    return {
        "window": f"{LOGGING_RETENTION_DAYS}d",
        "source": "Cloud Logging jsonPayload.event=tool_call",
        "first_ts": first_ts.isoformat() if first_ts else None,
        "last_ts": last_ts.isoformat() if last_ts else None,
        "truncated": truncated,
        "tools": tools,
        "clients": per_client,
        "matrix": matrix,
        "error_codes": error_codes,
        "by_sport": by_sport,
        "by_source": dict(sorted(by_source.items(), key=lambda kv: -kv[1])),
        "by_outcome": by_outcome,
        "by_hour": by_hour,
        "by_dow": by_dow,
        "success_over_time": {
            "days": days,
            "ok": [by_day[d]["ok"] for d in days],
            "error": [by_day[d]["error"] for d in days],
        },
        "total_ok": total_ok,
        "total_error": total_err,
        "total_calls": total,
        "error_rate": round(total_err / total, 4) if total else 0,
        "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "p50_ms": _percentile(latencies, 50),
        "p99_ms": _percentile(latencies, 99),
        "unique_tools": len(tools),
        "_events": events,
    }


# --------------------------------------------------------------------------- #
# Collector 4 — GitHub
# --------------------------------------------------------------------------- #
def collect_github() -> dict[str, Any]:
    token = _github_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}",
        headers=headers,
        timeout=15.0,
    )
    r.raise_for_status()
    data = r.json()
    result: dict[str, Any] = {
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "watchers": data.get("subscribers_count", 0),
        "created_at": (data.get("created_at") or "")[:10],
        "pushed_at": data.get("pushed_at"),
        "size_kb": data.get("size"),
        "default_branch": data.get("default_branch"),
        "license": (data.get("license") or {}).get("spdx_id"),
        "has_token": bool(token),
        "token_source": "env_or_gh",
    }

    rel = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/releases",
        headers=headers,
        timeout=15.0,
    )
    if rel.status_code == 200:
        releases = rel.json()
        result["release_count"] = len(releases)
        result["releases"] = [
            {
                "tag": x.get("tag_name"),
                "published": (x.get("published_at") or "")[:10],
                "name": x.get("name"),
            }
            for x in releases[:12]
        ]

    langs = httpx.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/languages",
        headers=headers,
        timeout=15.0,
    )
    if langs.status_code == 200:
        result["languages"] = langs.json()

    if token:
        for endpoint, key in [("views", "views"), ("clones", "clones")]:
            tr = httpx.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/traffic/{endpoint}",
                headers=headers,
                timeout=15.0,
            )
            if tr.status_code == 200:
                td = tr.json()
                result[key] = {
                    "total": td.get("count", 0),
                    "unique": td.get("uniques", 0),
                    "days": [item["timestamp"][:10] for item in td.get(key, [])],
                    "counts": [item["count"] for item in td.get(key, [])],
                    "uniques_by_day": [item["uniques"] for item in td.get(key, [])],
                }
            else:
                result[f"{key}_error"] = f"HTTP {tr.status_code}"

    return result


# --------------------------------------------------------------------------- #
# Collector 5 — PyPI (pypistats overall = full published history)
# --------------------------------------------------------------------------- #
def collect_pypi() -> dict[str, Any]:
    delays = [5, 15, 30]
    last_exc: Exception | None = None
    for attempt, delay in enumerate([*delays, None]):
        try:
            r = httpx.get(
                f"https://pypistats.org/api/packages/{PYPI_PACKAGE}/overall",
                params={"mirrors": "false"},
                headers={
                    "User-Agent": f"sportiq-mcp-dashboard/1.1 (+https://github.com/{GITHUB_REPO})"
                },
                timeout=20.0,
            )
            r.raise_for_status()
            rows = r.json().get("data", [])
            by_day: dict[str, int] = {}
            by_category: dict[str, int] = {}
            for row in rows:
                by_day[row["date"]] = by_day.get(row["date"], 0) + row["downloads"]
                cat = row.get("category") or "without_mirrors"
                by_category[cat] = by_category.get(cat, 0) + row["downloads"]
            days = sorted(by_day.keys())
            last_30 = days[-30:] if len(days) > 30 else days
            return {
                "window": "all_pypistats",
                "days": days,
                "downloads": [by_day[d] for d in days],
                "total": sum(by_day.values()),
                "total_30d": sum(by_day[d] for d in last_30),
                "first_day": days[0] if days else None,
                "last_day": days[-1] if days else None,
                "by_category": by_category,
            }
        except Exception as exc:
            last_exc = exc
            if delay is not None:
                print(f"  pypi         retry in {delay}s (attempt {attempt + 1})…")
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Collector 6 — GitHub Sponsors
# --------------------------------------------------------------------------- #
_SPONSORS_QUERY = """
query {
  viewer {
    monthlyEstimatedSponsorsIncomeInCents
    sponsorshipsAsMaintainer(
      first: 100, includePrivate: true, activeOnly: true,
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      totalCount
      nodes {
        createdAt
        isOneTimePayment
        sponsorEntity {
          __typename
          ... on User { login name }
          ... on Organization { login name }
        }
        tier { name monthlyPriceInDollars isOneTime }
      }
    }
  }
}
"""


def collect_sponsors() -> dict[str, Any]:
    token = _github_token()
    if not token:
        return {
            "has_token": False,
            "count": 0,
            "mrr_usd": 0,
            "sponsors": [],
            "tier_counts": {},
        }

    r = httpx.post(
        "https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json={"query": _SPONSORS_QUERY},
        timeout=20.0,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        msg = body["errors"][0].get("message", "GraphQL error")
        if "scopes" in msg.lower() or "read:user" in msg:
            return {
                "has_token": True,
                "scope_missing": True,
                "count": 0,
                "mrr_usd": 0,
                "sponsors": [],
                "tier_counts": {},
                "note": "Token needs the read:user scope for GitHub Sponsors.",
            }
        raise RuntimeError(msg)

    viewer = body["data"]["viewer"]
    sm = viewer["sponsorshipsAsMaintainer"]
    sponsors: list[dict[str, Any]] = []
    tier_counts: dict[str, int] = {}
    recurring_mrr = 0
    for node in sm.get("nodes", []):
        ent = node.get("sponsorEntity") or {}
        tier = node.get("tier") or {}
        price = tier.get("monthlyPriceInDollars") or 0
        one_time = bool(node.get("isOneTimePayment"))
        tier_name = tier.get("name") or "—"
        login = ent.get("login") or "private"
        sponsors.append(
            {
                "login": login,
                "name": ent.get("name") or login,
                "type": ent.get("__typename", "User"),
                "tier": tier_name,
                "price_usd": price,
                "one_time": one_time,
                "since": (node.get("createdAt") or "")[:10],
            }
        )
        tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1
        if not one_time:
            recurring_mrr += price

    cents = viewer.get("monthlyEstimatedSponsorsIncomeInCents") or 0
    return {
        "has_token": True,
        "count": sm.get("totalCount", 0),
        "mrr_usd": recurring_mrr,
        "est_monthly_income_usd": round(cents / 100, 2),
        "tier_counts": tier_counts,
        "sponsors": sponsors,
    }


# --------------------------------------------------------------------------- #
# Collector 8 — Dell home-server JSONL (post-GCP)
# --------------------------------------------------------------------------- #
def _is_healthcheck_event(ev: dict[str, Any]) -> bool:
    method = str(ev.get("method") or "").upper()
    if method == "GET":
        return True
    ua = ev.get("user_agent") or ""
    return classify_user_agent(ua) == "GCP healthcheck"


def _home_jsonl_paths() -> list[Path]:
    env = os.getenv("SPORTIQ_HOME_JSONL")
    if env:
        p = Path(env)
        return [p] if p.is_file() else []
    folder = ARCHIVE_DIR / "home-server"
    if not folder.is_dir():
        return []
    out: list[Path] = []
    for name in ("events.jsonl", "events.jsonl.1"):
        p = folder / name
        if p.is_file():
            out.append(p)
    out.extend(sorted(p for p in folder.glob("*.jsonl") if p not in out))
    return out


def collect_home_server() -> dict[str, Any]:
    """Read persisted Dell JSONL. Empty until compose is rebuilt + logs pulled."""
    paths = _home_jsonl_paths()
    if not paths:
        return {
            "window": "jsonl",
            "source": "home-server JSONL",
            "present": False,
            "lines_read": 0,
            "health_filtered": 0,
            "total_calls": 0,
            "total_ok": 0,
            "total_error": 0,
            "http_kept": 0,
            "clients": {},
            "client_buckets": {},
            "tools": [],
            "note": ("No local JSONL yet. After Dell rebuild: bash scripts/pull_home_analytics.sh"),
        }

    per_tool: dict[str, dict[str, Any]] = {}
    per_client: dict[str, int] = {}
    http_buckets: dict[str, int] = {}
    by_day: dict[str, dict[str, int]] = {}
    total_ok = total_err = 0
    health_filtered = 0
    lines_read = 0
    http_kept = 0
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    latencies: list[float] = []

    def _parse_ts(raw: Any) -> datetime | None:
        if not raw:
            return None
        try:
            ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            return None
        return ts.astimezone(UTC) if ts.tzinfo else ts.replace(tzinfo=UTC)

    for path in paths:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(ev, dict):
                    continue
                lines_read += 1
                if _is_healthcheck_event(ev):
                    health_filtered += 1
                    continue
                ts = _parse_ts(ev.get("timestamp") or ev.get("ts"))
                if ts:
                    first_ts = ts if first_ts is None or ts < first_ts else first_ts
                    last_ts = ts if last_ts is None or ts > last_ts else last_ts
                kind = ev.get("event")
                if kind == "mcp_request":
                    http_kept += 1
                    label = ev.get("client_name") or classify_user_agent(ev.get("user_agent") or "")
                    http_buckets[label] = http_buckets.get(label, 0) + 1
                    continue
                if kind != "tool_call":
                    continue
                tool = ev.get("tool") or "unknown"
                success = bool(ev.get("success"))
                latency = ev.get("latency_ms")
                label = ev.get("client_name") or classify_user_agent(ev.get("user_agent") or "")
                t = per_tool.setdefault(tool, {"calls": 0, "errors": 0, "lat": []})
                t["calls"] += 1
                if isinstance(latency, (int, float)):
                    t["lat"].append(float(latency))
                    latencies.append(float(latency))
                per_client[label] = per_client.get(label, 0) + 1
                day = _day(ts) if ts else "unknown"
                d = by_day.setdefault(day, {"ok": 0, "error": 0})
                if success:
                    total_ok += 1
                    d["ok"] += 1
                else:
                    t["errors"] += 1
                    total_err += 1
                    d["error"] += 1

    tools = []
    for name, t in per_tool.items():
        calls = t["calls"]
        lat = t["lat"]
        tools.append(
            {
                "tool": name,
                "sport": _sport_of(name),
                "calls": calls,
                "errors": t["errors"],
                "error_rate": round(t["errors"] / calls, 4) if calls else 0,
                "avg_ms": round(sum(lat) / len(lat), 1) if lat else 0,
                "p50_ms": _percentile(lat, 50),
                "p99_ms": _percentile(lat, 99),
            }
        )
    tools.sort(key=lambda r: r["calls"], reverse=True)
    days = sorted(d for d in by_day if d != "unknown")
    total = total_ok + total_err
    return {
        "window": "jsonl",
        "source": "home-server JSONL",
        "present": True,
        "paths": [str(p) for p in paths],
        "lines_read": lines_read,
        "health_filtered": health_filtered,
        "http_kept": http_kept,
        "client_buckets": http_buckets,
        "clients": per_client,
        "tools": tools,
        "success_over_time": {
            "days": days,
            "ok": [by_day[d]["ok"] for d in days],
            "error": [by_day[d]["error"] for d in days],
        },
        "total_ok": total_ok,
        "total_error": total_err,
        "total_calls": total,
        "error_rate": round(total_err / total, 4) if total else 0,
        "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "first_ts": first_ts.isoformat() if first_ts else None,
        "last_ts": last_ts.isoformat() if last_ts else None,
        "note": f"HEALTHCHECK GETs dropped: {health_filtered}. Pull with scripts/pull_home_analytics.sh",
    }


# --------------------------------------------------------------------------- #
# Collector 7 — GCP leftover inventory (no secrets)
# --------------------------------------------------------------------------- #
def collect_gcp_inventory() -> dict[str, Any]:
    def _run(args: list[str]) -> str:
        return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=30)

    buckets = []
    try:
        raw = _run(
            [
                "gcloud",
                "logging",
                "buckets",
                "list",
                f"--project={GCP_PROJECT}",
                "--format=json",
            ]
        )
        for b in json.loads(raw):
            buckets.append(
                {
                    "name": b.get("name", "").rsplit("/", 1)[-1],
                    "retention_days": b.get("retentionDays"),
                    "location": b.get("name", "").split("/")[3]
                    if "/locations/" in b.get("name", "")
                    else None,
                }
            )
    except Exception as exc:
        buckets = [{"_error": str(exc)}]

    scheduler = {}
    try:
        raw = _run(
            [
                "gcloud",
                "scheduler",
                "jobs",
                "describe",
                "sportiq-keepwarm",
                "--location=us-central1",
                f"--project={GCP_PROJECT}",
                "--format=json",
            ]
        )
        job = json.loads(raw)
        scheduler = {
            "state": job.get("state"),
            "schedule": job.get("schedule"),
            "uri": (job.get("httpTarget") or {}).get("uri"),
            "status": (job.get("status") or {}).get("code"),
        }
    except Exception as exc:
        scheduler = {"_error": str(exc)}

    artifacts_mb = None
    try:
        raw = _run(
            [
                "gcloud",
                "artifacts",
                "repositories",
                "describe",
                "cloud-run-source-deploy",
                "--location=us-central1",
                f"--project={GCP_PROJECT}",
                "--format=json",
            ]
        )
        repo = json.loads(raw)
        size = float(repo.get("sizeBytes") or 0)
        artifacts_mb = round(size / 1_000_000, 1)
    except Exception:
        artifacts_mb = None

    return {
        "project": GCP_PROJECT,
        "logging_buckets": buckets,
        "scheduler": scheduler,
        "artifact_registry_mb": artifacts_mb,
        "cloud_run_url": None,
        "live_url": "https://sportiq.utkarshgupta.org/mcp",
        "service_start": SERVICE_START.strftime("%Y-%m-%d"),
        "logging_retention_days": LOGGING_RETENTION_DAYS,
        "note": (
            "GCP project sportiq-mcp-prod is DELETE_REQUESTED (2026-09-02); Cloud Run "
            "is gone. Live telemetry is Dell JSONL. Cached GCP Monitoring/Logging "
            "panels are archive-only."
        ),
    }


# --------------------------------------------------------------------------- #
# Render + archive
# --------------------------------------------------------------------------- #
def render(payload: dict[str, Any]) -> None:
    template = TEMPLATE.read_text()
    json_str = json.dumps(_strip_private(payload), default=str).replace("</", "<\\/")
    html = template.replace("__DATA__", json_str)
    html = html.replace("__GENERATED__", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"))
    OUTPUT_HTML.write_text(html)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")


def archive(payload: dict[str, Any]) -> Path:
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%MZ")
    dest = ARCHIVE_DIR / stamp
    dest.mkdir(parents=True, exist_ok=True)
    public = _strip_private(payload)
    (dest / "payload.json").write_text(json.dumps(public, indent=2, default=str))
    ts_events = (payload.get("tool_stats") or {}).get("_events") or []
    http_events = (payload.get("http_logs") or {}).get("_events") or []
    _write_jsonl(dest / "tool_calls.jsonl", ts_events)
    _write_jsonl(dest / "http_mcp_events.jsonl", http_events)
    manifest = {
        "generated": datetime.now(UTC).isoformat(),
        "windows": {
            "cloud_run": (payload.get("cloud_run") or {}).get("window"),
            "tool_stats": (payload.get("tool_stats") or {}).get("window"),
            "http_logs": (payload.get("http_logs") or {}).get("window"),
            "pypi": (payload.get("pypi") or {}).get("window"),
        },
        "counts": {
            "tool_call_events": len(ts_events),
            "http_mcp_events": len(http_events),
            "cloud_run_requests": (payload.get("cloud_run") or {}).get("total_requests"),
        },
        "files": [
            "payload.json",
            "tool_calls.jsonl",
            "http_mcp_events.jsonl",
            "manifest.json",
        ],
        "pii": "no IPs stored; user-agents classified to coarse client labels only",
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2))
    latest = ARCHIVE_DIR / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    try:
        latest.symlink_to(dest.name)
    except OSError:
        (ARCHIVE_DIR / "LATEST_PATH.txt").write_text(str(dest))
    return dest


def main() -> None:
    print("Collecting sportiq-mcp analytics (all retained history, read-only)…")
    payload = {
        "cloud_run": _collect("cloud_run", collect_cloud_run),
        "tool_stats": _collect("tool_stats", collect_tool_stats),
        "http_logs": _collect("http_logs", collect_http_logs),
        "github": _collect("github", collect_github),
        "sponsors": _collect("sponsors", collect_sponsors),
        "pypi": _collect("pypi", collect_pypi, max_cache_hours=12),
        "gcp": _collect("gcp_inventory", collect_gcp_inventory),
        "home_server": _collect("home_server", collect_home_server),
    }
    # Back-compat alias for the old pie chart.
    http = payload["http_logs"]
    payload["ai_clients"] = {
        "buckets": http.get("client_buckets") or http.get("buckets") or {},
        "sampled": http.get("sampled"),
        "source": http.get("source_kind") or "user_agent",
        "_from_cache": http.get("_from_cache"),
        "_error": http.get("_error"),
        "_cached_at": http.get("_cached_at"),
    }
    for name, result in payload.items():
        status = (
            "cached" if result.get("_from_cache") else "error" if result.get("_error") else "live"
        )
        note = f"  ({result['_error']})" if result.get("_error") else ""
        extra = ""
        if name == "cloud_run" and result.get("total_requests"):
            extra = f"  requests={result['total_requests']} {result.get('first_day')}→{result.get('last_day')}"
        if name == "tool_stats" and result.get("total_calls") is not None:
            extra = f"  calls={result['total_calls']}"
        if name == "http_logs" and result.get("sampled") is not None:
            extra = f"  scanned={result['sampled']}"
        if name == "home_server" and result.get("lines_read") is not None:
            extra = f"  lines={result['lines_read']} health_drop={result.get('health_filtered')}"
        print(f"  {name:12s} {status}{extra}{note}")
    dest = archive(payload)
    print(f"\nArchived {dest}")
    render(payload)
    print(f"Wrote {OUTPUT_HTML}")
    if not os.getenv("DASHBOARD_NO_OPEN"):
        webbrowser.open(OUTPUT_HTML.as_uri())


if __name__ == "__main__":
    main()
