"""Separate maintainer dashboard; never writes the original dashboard or cache.

Offline: .venv/bin/python scripts/dashboard_live.py
Live:    .venv/bin/python scripts/dashboard_live.py --refresh --serve

Serves only the rendered HTML and aggregate JSON on 127.0.0.1:8765. Dell refreshes
every 5 minutes, GitHub hourly, PyPI every 12 hours. Cloudflare browser exports
are dated snapshots: put the aggregate snapshot in the new cache's cloudflare.json.
No production configuration changes, probes, GCP requests, or new dependencies.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).with_name("dashboard_live_template.html")
REPO = "Ninjabeam20/SportIQ-MCP"
SPORTS = ("football", "f1", "cricket", "cross-sport", "other")


def now() -> str:
    return datetime.now(UTC).isoformat()


def parse_time(value: Any) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def load_json(path: Path) -> dict:
    try:
        result = json.loads(path.read_text())
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False))
    temp.replace(path)


def legacy():
    spec = importlib.util.spec_from_file_location(
        "original_dashboard", Path(__file__).with_name("dashboard.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def client_label(event: dict, fallback) -> str:
    if event.get("client") or event.get("client_name"):
        return event.get("client") or event["client_name"]
    ua = (event.get("user_agent") or "").lower()
    for needle, name in (
        ("codex", "Codex"),
        ("mcpbeat", "MCPbeat"),
        ("sentineloracle", "SentinelOracle"),
        ("rokmcp", "RokMCP"),
        ("golemreach", "GolemreachTrustBot"),
        ("brickbluebot", "BrickBlueBot"),
        ("riaa-radariaagent", "RIAA RadarIAAgent"),
        ("agent-index-prober", "Agent Index Prober"),
        ("tendle", "Tendle"),
        ("faceabotprobe", "FaceabotProbe"),
        ("aiohttp", "Python aiohttp"),
        ("glama", "Glama"),
    ):
        if needle in ua:
            return name
    return fallback(ua)


def read_events(paths: list[Path], era: str) -> tuple[list[dict], int]:
    """Union snapshots by maximum multiplicity, retaining repeated rows within a file."""
    union: Counter = Counter()
    records = {}
    invalid = 0
    classifier = legacy().classify_user_agent
    for path in paths:
        counts: Counter = Counter()
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError("not an object")
                except ValueError:
                    invalid += 1
                    continue
                kind = event.get("event") or ("tool_call" if event.get("tool") else "mcp_request")
                ts = parse_time(event.get("timestamp") or event.get("ts"))
                value = event.get("latency_ms")
                latency = (
                    float(value)
                    if isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value >= 0
                    else None
                )
                normalized = {
                    "era": era,
                    "event": kind,
                    "ts": ts.isoformat() if ts else None,
                    "tool": event.get("tool"),
                    "success": event.get("success"),
                    "outcome": event.get("outcome"),
                    "latency_ms": latency,
                    "client": client_label(event, classifier),
                    "method": event.get("method"),
                    "source": event.get("source"),
                    "error": event.get("error"),
                    "is_stale": event.get("is_stale"),
                }
                # Client classification can improve between exports; it is not
                # an event identifier. Preserve the richer observed label.
                identity = {k: v for k, v in normalized.items() if k != "client"}
                key = json.dumps(identity, sort_keys=True)
                if key not in records or records[key]["client"] in ("unknown", "other"):
                    records[key] = normalized
                counts[key] += 1
        union |= counts
    return [records[key].copy() for key, count in union.items() for _ in range(count)], invalid


def merge_daily(snapshots: list[dict], field: str) -> dict[str, int]:
    """Newest observation replaces an overlapping day; missing dates stay missing."""
    result = {}
    for snapshot in snapshots:
        result.update(zip(snapshot.get("days", []), snapshot.get(field, []), strict=False))
    return dict(sorted(result.items()))


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(fraction * len(ordered)) - 1)], 1)


def summarize(events: list[dict]) -> dict:
    calls = [
        e for e in events if e.get("event") == "tool_call" and e.get("tool") != "sportiq_health"
    ]
    health = [e for e in events if e.get("tool") == "sportiq_health"]
    http = [e for e in events if e.get("event") == "mcp_request"]
    lat = [e["latency_ms"] for e in calls if isinstance(e.get("latency_ms"), (int, float))]
    errors = [e for e in calls if e.get("success") is False]
    by_tool: dict[str, list] = defaultdict(list)
    daily: dict[str, dict] = {}
    hourly = [0] * 24
    weekdays = [0] * 7
    matrix: dict[str, Counter] = defaultdict(Counter)
    for e in calls:
        by_tool[e.get("tool") or "unknown"].append(e)
        matrix[e.get("client") or "unknown"][e.get("tool") or "unknown"] += 1
        ts = parse_time(e.get("ts"))
        if ts:
            day = daily.setdefault(ts.date().isoformat(), {"ok": 0, "error": 0, "unknown": 0})
            day[
                "ok"
                if e.get("success") is True
                else "error"
                if e.get("success") is False
                else "unknown"
            ] += 1
            hourly[ts.hour] += 1
            weekdays[ts.weekday()] += 1
    tools = []
    for name, rows in by_tool.items():
        samples = [e["latency_ms"] for e in rows if isinstance(e.get("latency_ms"), (int, float))]
        sport = name.split("_")[0]
        sport = "cross-sport" if sport == "cross" else sport if sport in SPORTS else "other"
        tools.append(
            {
                "tool": name,
                "sport": sport,
                "calls": len(rows),
                "errors": sum(e.get("success") is False for e in rows),
                "avg_ms": round(sum(samples) / len(samples), 1) if samples else None,
                "p50_ms": percentile(samples, 0.5),
                "p95_ms": percentile(samples, 0.95),
                "p99_ms": percentile(samples, 0.99),
                "max_ms": max(samples) if samples else None,
                "stale": sum(e.get("is_stale") is True for e in rows),
            }
        )
    tools.sort(key=lambda t: (SPORTS.index(t["sport"]), -t["calls"], t["tool"]))
    timestamps = sorted(e["ts"] for e in events if e.get("ts"))
    return {
        "total_calls": len(calls),
        "errors": len(errors),
        "ok": sum(e.get("success") is True for e in calls),
        "error_rate": len(errors) / len(calls) if calls else None,
        "health_calls": len(health),
        "health_errors": sum(e.get("success") is False for e in health),
        "http_get": sum(e.get("method") == "GET" for e in http),
        "http_other": sum(e.get("method") != "GET" for e in http),
        "http_methods": dict(Counter(e.get("method") or "unrecorded" for e in http)),
        "latency_samples": len(lat),
        "avg_ms": round(sum(lat) / len(lat), 1) if lat else None,
        "p50_ms": percentile(lat, 0.5),
        "p95_ms": percentile(lat, 0.95),
        "p99_ms": percentile(lat, 0.99),
        "slow_1s": sum(v > 1000 for v in lat),
        "slow_5s": sum(v > 5000 for v in lat),
        "slow_10s": sum(v > 10000 for v in lat),
        "max_ms": max(lat) if lat else None,
        "tools": tools,
        "daily": dict(sorted(daily.items())),
        "hours_utc": hourly,
        "weekdays_utc": weekdays,
        "clients": dict(Counter(e.get("client") or "unknown" for e in calls)),
        "http_clients": dict(Counter(e.get("client") or "unknown" for e in http)),
        "matrix": dict(matrix),
        "sources": dict(Counter(e.get("source") or "unrecorded" for e in calls)),
        "error_codes": dict(Counter(e.get("error") or "unrecorded" for e in errors)),
        "stale_calls": sum(e.get("is_stale") is True for e in calls),
        "first_ts": timestamps[0] if timestamps else None,
        "last_ts": timestamps[-1] if timestamps else None,
        "recent_errors": sorted(errors, key=lambda e: e.get("ts") or "", reverse=True)[:25],
        "slowest": sorted(
            (e for e in calls if e.get("latency_ms") is not None),
            key=lambda e: e["latency_ms"],
            reverse=True,
        )[:15],
    }


def collect_cached(folder: Path, name: str, fn, ttl: int, *, online: bool) -> dict:
    path = folder / f"{name}.json"
    cached = load_json(path)
    stamp = parse_time(cached.get("_cached_at"))
    fresh = stamp is not None and (datetime.now(UTC) - stamp).total_seconds() < ttl
    attempt = parse_time(cached.get("_attempted_at"))
    cooling_down = (
        cached.get("_error") and attempt and (datetime.now(UTC) - attempt).total_seconds() < ttl
    )
    if not online or fresh or cooling_down:
        return {**cached, "_state": "cached" if fresh else "stale" if stamp else "unavailable"}
    try:
        data = {**fn(), "_cached_at": now()}
        write_json(path, data)
        return {**data, "_state": "fresh"}
    except Exception as exc:
        # Do not embed exception URLs, headers, tokens, or subprocess stderr in HTML.
        detail = (
            f"HTTP {exc.response.status_code}"
            if isinstance(exc, httpx.HTTPStatusError)
            else type(exc).__name__
        )
        failed = {
            **cached,
            "_error": detail,
            "_attempted_at": now(),
        }
        write_json(path, failed)
        return {**failed, "_state": "stale" if stamp else "unavailable"}


def collect_github() -> dict:
    token = legacy()._github_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(headers=headers, timeout=25) as client:

        def get(suffix):
            response = client.get(f"https://api.github.com/repos/{REPO}" + suffix)
            response.raise_for_status()
            return response.json()

        data = get("")
        result = {
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "watchers": data["subscribers_count"],
            "pushed_at": data["pushed_at"],
            "open_issues": data["open_issues_count"],
            "endpoint_errors": {},
        }
        for endpoint in ("views", "clones", "popular/referrers", "popular/paths"):
            key = endpoint.split("/")[-1]
            try:
                payload = get(f"/traffic/{endpoint}")
                if key in ("views", "clones"):
                    result[key] = {
                        "total": payload["count"],
                        "unique": payload["uniques"],
                        "days": [r["timestamp"][:10] for r in payload[key]],
                        "counts": [r["count"] for r in payload[key]],
                        "uniques_by_day": [r["uniques"] for r in payload[key]],
                    }
                else:
                    result[key] = payload
            except httpx.HTTPStatusError as exc:
                result["endpoint_errors"][key] = f"HTTP {exc.response.status_code}"
        for suffix, key in (
            ("forks", "fork_owners"),
            ("releases", "releases"),
            ("stargazers", "stargazers"),
        ):
            try:
                rows = []
                for page in range(1, 101):
                    batch = get(f"/{suffix}?per_page=100&page={page}")
                    rows.extend(batch)
                    if len(batch) < 100:
                        break
                if key == "fork_owners":
                    result[key] = [
                        {
                            "login": r["owner"]["login"],
                            "url": r["html_url"],
                            "created_at": r["created_at"],
                        }
                        for r in rows
                    ]
                elif key == "stargazers":
                    result[key] = [{"login": r["login"], "url": r["html_url"]} for r in rows]
                else:
                    result[key] = [
                        {
                            "tag": r["tag_name"],
                            "published": r["published_at"],
                            "downloads": sum(a["download_count"] for a in r.get("assets", [])),
                        }
                        for r in rows
                    ]
            except httpx.HTTPStatusError as exc:
                result["endpoint_errors"][key] = f"HTTP {exc.response.status_code}"
        return result


def collect_pypi() -> dict:
    with httpx.Client(
        timeout=30,
        headers={"User-Agent": f"sportiq-local-analytics/2 (+https://github.com/{REPO})"},
    ) as client:
        response = client.get(
            "https://pypistats.org/api/packages/sportiq-mcp/overall", params={"mirrors": "false"}
        )
        response.raise_for_status()
        # Never add with_mirrors and without_mirrors: they overlap.
        rows = [r for r in response.json()["data"] if r["category"] == "without_mirrors"]
        days = {r["date"]: r["downloads"] for r in rows}
        return {
            "days": sorted(days),
            "downloads": [days[d] for d in sorted(days)],
            "total": sum(days.values()),
        }


def pull_dell(folder: Path) -> dict:
    raw = folder / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / "dell-retained.jsonl"
    temp = path.with_suffix(".part")
    command = 'docker exec sportiq sh -c "cat /var/log/sportiq/events.jsonl; if test -f /var/log/sportiq/events.jsonl.1; then cat /var/log/sportiq/events.jsonl.1; fi"'
    try:
        with temp.open("xb") as output:
            subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "home-server", command],
                stdout=output,
                stderr=subprocess.PIPE,
                timeout=90,
                check=True,
            )
        if not temp.stat().st_size:
            raise ValueError("empty Dell log export")
        events, invalid = read_events([*sorted(raw.glob("dell-*.jsonl")), temp], "dell")
        # Keep a cumulative union, not a fresh 30 MB copy every five minutes.
        retained = path.with_suffix(".normalized")
        with retained.open("w") as output:
            for event in events:
                output.write(json.dumps(event) + "\n")
        retained.replace(path)
        return {"file": path.name, "bytes": path.stat().st_size, "invalid_lines": invalid}
    finally:
        temp.unlink(missing_ok=True)


def collect_runtime() -> dict:
    command = "docker inspect --format '{{json .State}}' sportiq; docker stats --no-stream --format '{{json .}}' sportiq"
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "home-server", command],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    lines = result.stdout.splitlines()
    state, stats = json.loads(lines[0]), json.loads(lines[1])
    return {
        "status": state.get("Status"),
        "started_at": state.get("StartedAt"),
        "oom_killed": state.get("OOMKilled"),
        "health": state.get("Health", {}).get("Status"),
        "cpu": stats.get("CPUPerc"),
        "memory": stats.get("MemUsage"),
        "memory_pct": stats.get("MemPerc"),
        "network_io": stats.get("NetIO"),
        "pids": stats.get("PIDs"),
    }


def build(*, online: bool = False) -> dict:
    folder = ROOT / "analytics-archive/live-dashboard"
    archive_cache = ROOT / ".dashboard_cache"
    original = {
        name: load_json(archive_cache / f"{name}.json")
        for name in ("cloud_run", "tool_stats", "http_logs", "github", "pypi", "sponsors")
    }
    jobs = {
        "dell_pull": (lambda: pull_dell(folder), 300),
        "runtime": (collect_runtime, 300),
        "github": (collect_github, 3600),
        "pypi": (collect_pypi, 43200),
    }
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            key: pool.submit(collect_cached, folder, key, fn, ttl, online=online)
            for key, (fn, ttl) in jobs.items()
        }
        sources = {key: future.result() for key, future in futures.items()}
    gcp_paths = sorted((ROOT / "analytics-archive").glob("20*/tool_calls.jsonl"))
    gcp_events, gcp_invalid = read_events(gcp_paths, "gcp")
    home_paths = sorted((ROOT / "analytics-archive/home-server").glob("*.jsonl"))
    home_paths += sorted((folder / "raw").glob("dell-*.jsonl"))
    dell_events, dell_invalid = read_events(home_paths, "dell")
    # Seed snapshots are read-only, newer successful snapshots are retained separately.
    snapshots = [
        load_json(p) for p in sorted((ROOT / "analytics-archive").glob("20*/payload.json"))
    ]
    snapshots += [{"github": original["github"], "pypi": original["pypi"]}]
    snapshots += [load_json(p) for p in sorted((folder / "snapshots").glob("*.json"))]
    snapshots += [sources]
    for name in ("github", "pypi"):
        if not sources[name].get("_cached_at") and original[name]:
            sources[name] = {
                **original[name],
                "_state": "stale",
                "_error": sources[name].get("_error"),
            }
    downloads = merge_daily([s.get("pypi", {}) for s in snapshots], "downloads")
    history = {
        key: merge_daily([s.get("github", {}).get(key, {}) for s in snapshots], "counts")
        for key in ("views", "clones")
    }
    cutoff_time = datetime.now(UTC) - timedelta(days=30)
    cutoff = cutoff_time.date().isoformat()
    pull = sources["dell_pull"]
    dell = {
        **summarize(dell_events),
        "_state": pull["_state"] if home_paths else "unavailable",
        "_cached_at": pull.get("_cached_at"),
        "_error": pull.get("_error"),
        "invalid_lines": dell_invalid,
    }
    if home_paths and not dell["_cached_at"]:
        dell["_state"] = "stale"
        dell["_cached_at"] = datetime.fromtimestamp(
            max(p.stat().st_mtime for p in home_paths), UTC
        ).isoformat()
    cf = load_json(folder / "cloudflare.json")
    payload = {
        "generated_at": now(),
        "online": online,
        "dell": dell,
        "runtime": sources["runtime"],
        "dell_30d": summarize(
            [e for e in dell_events if (e.get("ts") or "") >= cutoff_time.isoformat()]
        ),
        "gcp": {
            **original["cloud_run"],
            "_state": "archive" if original["cloud_run"] else "unavailable",
        },
        "gcp_tools": {**summarize(gcp_events), "invalid_lines": gcp_invalid, "_state": "archive"},
        "gcp_tool_details": {
            k: v for k, v in original["tool_stats"].items() if not k.startswith("_events")
        },
        "gcp_http": {k: v for k, v in original["http_logs"].items() if not k.startswith("_events")},
        "combined": summarize(gcp_events + dell_events),
        "github": sources["github"],
        "github_history": history,
        "pypi": {
            **sources["pypi"],
            "daily": downloads,
            "retained_total": sum(downloads.values()),
            "last30_total": sum(
                n
                for day, n in downloads.items()
                if cutoff <= day < datetime.now(UTC).date().isoformat()
            ),
            "first_day": min(downloads, default=None),
            "last_day": max(downloads, default=None),
        },
        "cloudflare": {**cf, "_state": "snapshot" if cf else "unavailable"},
        "sponsors_archive": original["sponsors"],
        "sources": [
            {
                "title": "GitHub traffic: 14-day window",
                "url": "https://docs.github.com/en/rest/metrics/traffic",
            },
            {
                "title": "PyPI downloads: updated daily, 180-day retention",
                "url": "https://pypistats.org/api/",
            },
            {
                "title": "Cloudflare hostname analytics",
                "url": "https://developers.cloudflare.com/analytics/graphql-api/tutorials/end-customer-analytics/",
            },
        ],
    }
    if online:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        write_json(
            folder / "snapshots" / f"{stamp}.json",
            {"github": sources["github"], "pypi": sources["pypi"]},
        )
    return payload


def render(data: dict, output: Path, template: Path = TEMPLATE) -> None:
    serialized = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    content = template.read_text().replace("__DATA__", serialized)
    temp = output.with_suffix(".tmp")
    temp.write_text(content)
    temp.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh", action="store_true", help="Read approved external sources, respecting TTLs"
    )
    parser.add_argument(
        "--serve", action="store_true", help="Serve a local dashboard and refresh every minute"
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    output = ROOT / "dashboard_live.html"
    data = build(online=args.refresh)
    render(data, output)
    print(f"Wrote {output}", flush=True)
    print(
        json.dumps(
            {
                "dell_calls": data["dell"]["total_calls"],
                "dell_errors": data["dell"]["errors"],
                "source_states": {
                    k: data[k]["_state"] for k in ("dell", "github", "pypi", "cloudflare")
                },
            }
        ),
        flush=True,
    )
    if not args.serve:
        return
    lock = threading.Lock()
    stop = threading.Event()

    def update():
        nonlocal data
        while not stop.wait(60):
            try:
                new = build(online=args.refresh)
                render(new, output)
                with lock:
                    data = new
            except Exception as exc:
                print(f"Refresh failed: {type(exc).__name__}", flush=True)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = self.path.split("?", 1)[0]
            if route == "/data.json":
                with lock:
                    body = json.dumps(data, allow_nan=False).encode()
                content_type = "application/json"
            elif route in ("/", "/dashboard_live.html"):
                body = output.read_bytes()
                content_type = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src data:; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(target=update, daemon=True).start()
    print(f"Dashboard: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
