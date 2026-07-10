"""Local analytics dashboard for sportiq-mcp.

Read-only. Pulls aggregate usage from several sources, renders a static
``dashboard.html`` with Chart.js (CDN), and opens it in the browser. No server,
no hosting, no cost. Run on demand::

    uv sync --extra dev --extra analytics   # standard setup (analytics = the GCP client libs)
    gcloud auth application-default login   # one-time: GCP read access (ADC)
    uv run python scripts/dashboard.py

Each collector degrades independently: if an API is down or auth is missing,
that panel shows the last cached value (``.dashboard_cache/``) or an empty
state, and the rest of the dashboard still renders.

What this CANNOT show: individual user identity. The MCP server is anonymous
(BYO-keys, no auth), so every metric here is aggregate by design — request
counts, latency, coarse AI-client guesses from User-Agent, never named users.
"""

from __future__ import annotations

import json
import os
import time
import webbrowser
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

# --- Constants: the four identifiers for this project (verified 2026-06-12) ---
GCP_PROJECT = "sportiq-mcp-prod"
CLOUD_RUN_SERVICE = "sportiq-mcp"
CLOUD_RUN_REGION = "us-central1"
GITHUB_REPO = "Ninjabeam20/SportIQ-MCP"
PYPI_PACKAGE = "sportiq-mcp"

LOOKBACK_DAYS = 30

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".dashboard_cache"
TEMPLATE = Path(__file__).resolve().parent / "dashboard_template.html"
OUTPUT_HTML = REPO_ROOT / "dashboard.html"

# Best-effort User-Agent → AI-client classifier. MCP clients frequently connect
# through generic HTTP libraries, so "unknown"/"python-httpx" buckets are
# expected to be large. This is a heuristic, not ground truth.
_UA_RULES: list[tuple[str, str]] = [
    ("claude", "Claude"),
    ("anthropic", "Claude"),
    ("chatgpt", "ChatGPT"),
    ("openai", "ChatGPT"),
    ("cursor", "Cursor"),
    ("cline", "Cline"),
    ("windsurf", "Windsurf"),
    ("vscode", "VS Code"),
    ("node", "Node client"),
    ("python-httpx", "python-httpx"),
    ("httpx", "python-httpx"),
    ("python-requests", "python-requests"),
    ("go-http", "Go client"),
]


def classify_user_agent(ua: str) -> str:
    """Map a raw User-Agent string to a coarse AI-client label."""
    if not ua:
        return "unknown"
    low = ua.lower()
    for needle, label in _UA_RULES:
        if needle in low:
            return label
    return "other"


# --------------------------------------------------------------------------- #
# Cache helpers — every collector writes its last-good result here so the
# dashboard still renders offline / when an upstream is unavailable.
# --------------------------------------------------------------------------- #
def _cache_write(name: str, payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    payload["_cached_at"] = datetime.now(UTC).isoformat()
    (CACHE_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2))


def _cache_read(name: str) -> dict[str, Any]:
    path = CACHE_DIR / f"{name}.json"
    if path.exists():
        data = json.loads(path.read_text())
        data["_from_cache"] = True
        return data
    return {"_unavailable": True}


def _cache_age_hours(name: str) -> float | None:
    """Return how many hours old the cached entry is, or None if no cache."""
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
    """Run a collector; on any failure fall back to its cached value.

    If *max_cache_hours* > 0 and the cached entry is younger than that
    threshold, skip the live fetch entirely (avoids hitting rate limits).
    """
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


# --------------------------------------------------------------------------- #
# Collector 1 — Cloud Run request volume + latency (Cloud Monitoring)
# --------------------------------------------------------------------------- #
def collect_cloud_run() -> dict[str, Any]:
    from google.cloud import monitoring_v3

    client = monitoring_v3.MetricServiceClient()
    project = f"projects/{GCP_PROJECT}"
    now = datetime.now(UTC)
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": int(now.timestamp())},
            "start_time": {"seconds": int((now - timedelta(days=LOOKBACK_DAYS)).timestamp())},
        }
    )
    service_filter = (
        f'resource.labels.service_name="{CLOUD_RUN_SERVICE}" '
        f'resource.labels.location="{CLOUD_RUN_REGION}"'
    )

    # --- request_count, bucketed daily, split by response-code class ---
    counts_by_day: dict[str, dict[str, int]] = {}
    agg_count = monitoring_v3.Aggregation(
        {
            "alignment_period": {"seconds": 86400},
            "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
            "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
            "group_by_fields": ["metric.labels.response_code_class"],
        }
    )
    rc_series = client.list_time_series(
        request={
            "name": project,
            "filter": (
                'metric.type="run.googleapis.com/request_count" ' + service_filter
            ),
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": agg_count,
        }
    )
    for series in rc_series:
        klass = series.metric.labels.get("response_code_class", "other")
        for point in series.points:
            day = datetime.fromtimestamp(
                point.interval.end_time.timestamp(), tz=UTC
            ).strftime("%Y-%m-%d")
            counts_by_day.setdefault(day, {})
            counts_by_day[day][klass] = counts_by_day[day].get(klass, 0) + int(
                point.value.int64_value or point.value.double_value
            )

    # --- request_latencies (p50 / p99), bucketed daily ---
    def _latency(percentile: int) -> dict[str, float]:
        aligner = (
            monitoring_v3.Aggregation.Aligner.ALIGN_PERCENTILE_50
            if percentile == 50
            else monitoring_v3.Aggregation.Aligner.ALIGN_PERCENTILE_99
        )
        agg = monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": 86400},
                "per_series_aligner": aligner,
                "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_MEAN,
            }
        )
        out: dict[str, float] = {}
        series = client.list_time_series(
            request={
                "name": project,
                "filter": (
                    'metric.type="run.googleapis.com/request_latencies" '
                    + service_filter
                ),
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": agg,
            }
        )
        for s in series:
            for point in s.points:
                day = datetime.fromtimestamp(
                    point.interval.end_time.timestamp(), tz=UTC
                ).strftime("%Y-%m-%d")
                out[day] = round(point.value.double_value, 1)
        return out

    days = sorted(counts_by_day.keys())
    return {
        "days": days,
        "counts_by_day": counts_by_day,
        "p50": _latency(50),
        "p99": _latency(99),
        "total_requests": sum(
            sum(v.values()) for v in counts_by_day.values()
        ),
    }


# --------------------------------------------------------------------------- #
# Collector 2 — AI-client breakdown from Cloud Logging User-Agent
# --------------------------------------------------------------------------- #
def collect_ai_clients() -> dict[str, Any]:
    from google.cloud import logging_v2

    client = logging_v2.Client(project=GCP_PROJECT)
    since = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    # Prefer the structured `mcp_request` events emitted by ClientInfoMiddleware
    # (clean `client_name`); fall back to User-Agent parsing for older revisions
    # / requests that predate the middleware deploy.
    log_filter = (
        'resource.type="cloud_run_revision" '
        f'resource.labels.service_name="{CLOUD_RUN_SERVICE}" '
        f'timestamp>="{since}" '
        '(jsonPayload.event="mcp_request" OR httpRequest.requestUrl:"/mcp")'
    )
    buckets: dict[str, int] = {}
    source = "user_agent"  # upgraded to "client_info" if clean names are present
    # Cap the scan so a chatty service doesn't make the dashboard hang.
    for i, entry in enumerate(
        client.list_entries(filter_=log_filter, page_size=1000)
    ):
        if i >= 5000:
            break
        payload = getattr(entry, "payload", None)
        # 1) Structured middleware event with a clean client name?
        if isinstance(payload, dict) and payload.get("event") == "mcp_request":
            name = payload.get("client_name")
            if name:
                buckets[name] = buckets.get(name, 0) + 1
                source = "client_info"
                continue
            ua = payload.get("user_agent", "")
            label = classify_user_agent(ua or "")
            buckets[label] = buckets.get(label, 0) + 1
            continue
        # 2) Fallback: raw httpRequest User-Agent.
        http = getattr(entry, "http_request", None) or {}
        ua = http.get("userAgent", "") if isinstance(http, dict) else getattr(
            http, "user_agent", ""
        )
        label = classify_user_agent(ua or "")
        buckets[label] = buckets.get(label, 0) + 1
    return {"buckets": buckets, "sampled": sum(buckets.values()), "source": source}


# --------------------------------------------------------------------------- #
# Collector 3 — Per-tool telemetry from the `tool_call` structured log events
# (emitted by core/tool_telemetry.py). This is the only source that knows which
# *tool* ran, whether it *actually* succeeded (MCP errors are HTTP 200, so Cloud
# Run's 2xx panel can't tell), how long the tool itself took, and which client
# called it. Answers: calls by tool, error rate by tool, latency by tool, calls
# by client, and the client-by-tool matrix.
# --------------------------------------------------------------------------- #
def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round((pct / 100.0) * (len(ordered) - 1)))
    return round(ordered[idx], 1)


def collect_tool_stats() -> dict[str, Any]:
    from google.cloud import logging_v2

    client = logging_v2.Client(project=GCP_PROJECT)
    since = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
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
    total_ok = total_err = 0

    for i, entry in enumerate(client.list_entries(filter_=log_filter, page_size=1000)):
        if i >= 50000:  # generous cap; keeps a chatty service from hanging the run
            break
        p = getattr(entry, "payload", None)
        if not isinstance(p, dict):
            continue
        tool = p.get("tool") or "unknown"
        success = bool(p.get("success"))
        latency = p.get("latency_ms")
        # Same client-resolution rule as collect_ai_clients: clean name first,
        # else classify the User-Agent.
        label = p.get("client_name") or classify_user_agent(p.get("user_agent") or "")

        t = per_tool.setdefault(tool, {"calls": 0, "errors": 0, "lat": []})
        t["calls"] += 1
        if isinstance(latency, (int, float)):
            t["lat"].append(float(latency))
        per_client[label] = per_client.get(label, 0) + 1
        matrix.setdefault(label, {})
        matrix[label][tool] = matrix[label].get(tool, 0) + 1

        ts = getattr(entry, "timestamp", None)
        day = ts.strftime("%Y-%m-%d") if ts else "unknown"
        d = by_day.setdefault(day, {"ok": 0, "error": 0})
        if success:
            total_ok += 1
            d["ok"] += 1
        else:
            t["errors"] += 1
            total_err += 1
            d["error"] += 1
            code = p.get("error") or p.get("outcome") or "error"
            error_codes[code] = error_codes.get(code, 0) + 1

    tools = []
    for name, t in per_tool.items():
        calls = t["calls"]
        lat = t["lat"]
        tools.append(
            {
                "tool": name,
                "calls": calls,
                "errors": t["errors"],
                "error_rate": round(t["errors"] / calls, 4) if calls else 0,
                "avg_ms": round(sum(lat) / len(lat), 1) if lat else 0,
                "p99_ms": _percentile(lat, 99),
            }
        )
    tools.sort(key=lambda r: r["calls"], reverse=True)

    days = sorted(d for d in by_day if d != "unknown")
    return {
        "tools": tools,
        "clients": per_client,
        "matrix": matrix,
        "error_codes": error_codes,
        "success_over_time": {
            "days": days,
            "ok": [by_day[d]["ok"] for d in days],
            "error": [by_day[d]["error"] for d in days],
        },
        "total_ok": total_ok,
        "total_error": total_err,
        "total_calls": total_ok + total_err,
    }


# --------------------------------------------------------------------------- #
# Collector 4 — GitHub stars / forks / traffic (token optional)
# --------------------------------------------------------------------------- #
def collect_github() -> dict[str, Any]:
    token = os.getenv("GITHUB_TOKEN")
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
        "has_token": bool(token),
    }

    if token:
        # Traffic endpoints require push access + token
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

    return result


# --------------------------------------------------------------------------- #
# Collector 5 — PyPI downloads (pypistats, no auth)
# --------------------------------------------------------------------------- #
def collect_pypi() -> dict[str, Any]:
    # pypistats.org rate-limits aggressively; retry with backoff before giving up.
    delays = [5, 15, 30]
    last_exc: Exception | None = None
    for attempt, delay in enumerate([*delays, None]):
        try:
            r = httpx.get(
                f"https://pypistats.org/api/packages/{PYPI_PACKAGE}/overall",
                params={"mirrors": "false"},
                headers={"User-Agent": f"sportiq-mcp-dashboard/1.0 (+https://github.com/{GITHUB_REPO})"},
                timeout=20.0,
            )
            r.raise_for_status()
            rows = r.json().get("data", [])
            by_day: dict[str, int] = {}
            for row in rows:
                by_day[row["date"]] = by_day.get(row["date"], 0) + row["downloads"]
            days = sorted(by_day.keys())[-LOOKBACK_DAYS:]
            return {
                "days": days,
                "downloads": [by_day[d] for d in days],
                "total": sum(by_day[d] for d in days),
            }
        except Exception as exc:
            last_exc = exc
            if delay is not None:
                print(f"  pypi         retry in {delay}s (attempt {attempt + 1})…")
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Collector 6 — GitHub Sponsors (who / what tier / recurring vs one-time)
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
    """GitHub Sponsors — sponsor count, each sponsor's tier + price, recurring vs
    one-time, join date, and estimated monthly income.

    NOTE on "what each sponsor is using": that is intentionally NOT here. Every
    sponsor connects with the same shared Tier-0 key (``/u/<key>/mcp``), so the
    server cannot attribute a tool call to a person — aggregate tool usage lives
    in the Tools panels. Per-sponsor attribution requires the V2b per-user keys
    (mint a unique key per sponsorship via the GitHub webhook). Until then this
    panel covers identity + billing only.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"has_token": False, "count": 0, "mrr_usd": 0, "sponsors": [], "tier_counts": {}}

    r = httpx.post(
        "https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json={"query": _SPONSORS_QUERY},
        timeout=20.0,
    )
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        # Most common cause: the token lacks the `read:user` / sponsors scope.
        raise RuntimeError(body["errors"][0].get("message", "GraphQL error"))

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
# Render
# --------------------------------------------------------------------------- #
def render(payload: dict[str, Any]) -> None:
    template = TEMPLATE.read_text()
    json_str = json.dumps(payload, default=str).replace("</", "<\\/")
    html = template.replace("__DATA__", json_str)
    html = html.replace("__GENERATED__", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"))
    OUTPUT_HTML.write_text(html)


def main() -> None:
    print("Collecting sportiq-mcp analytics (read-only, local)…")
    payload = {
        "cloud_run": _collect("cloud_run", collect_cloud_run),
        "tool_stats": _collect("tool_stats", collect_tool_stats),
        "ai_clients": _collect("ai_clients", collect_ai_clients),
        "github": _collect("github", collect_github),
        "sponsors": _collect("sponsors", collect_sponsors),
        "pypi": _collect("pypi", collect_pypi, max_cache_hours=12),
    }
    for name, result in payload.items():
        status = (
            "cached" if result.get("_from_cache")
            else "error" if result.get("_error")
            else "live"
        )
        note = f"  ({result['_error']})" if result.get("_error") else ""
        print(f"  {name:12s} {status}{note}")
    render(payload)
    print(f"\nWrote {OUTPUT_HTML}")
    if not os.getenv("DASHBOARD_NO_OPEN"):
        webbrowser.open(OUTPUT_HTML.as_uri())


if __name__ == "__main__":
    main()
