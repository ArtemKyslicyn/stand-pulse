"""pulse — on-call CLI for Stand Pulse MCP (watch, probe, scheduled digest)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = os.environ.get("MCP_URL", "https://aichallenge.arcilite.ru/mcp")


def _text(result: Any) -> str:
    chunks: list[str] = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if text:
            chunks.append(str(text))
    return "\n".join(chunks) if chunks else str(result)


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _pretty(raw: str) -> str:
    parsed = _parse_json(raw)
    if parsed:
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    return raw


def format_watch(brief: dict[str, Any]) -> str:
    severity = str(brief.get("severity") or "ok").upper()
    lines = [
        f"STAND WATCH · {severity}",
        str(brief.get("summary") or ""),
    ]
    latest = brief.get("latest_probe") or {}
    if latest:
        flag = "up" if latest.get("ok") else "down"
        delta = brief.get("latency_delta_ms")
        extra = f"  Δ {delta:+d} мс" if isinstance(delta, int) else ""
        lines.append(f"probe  {flag}  {latest.get('latency_ms', '—')} мс{extra}")
    incidents = brief.get("open_incidents") or []
    if not incidents:
        lines.append("incidents  none")
    else:
        lines.append(f"incidents  {len(incidents)} open")
        for item in incidents:
            ack = "ack" if item.get("acked") else "new"
            lines.append(
                f"  [{item.get('severity')}] {item.get('title')}  ({ack})  {item.get('id')}"
            )
    return "\n".join(lines)


def _mcp_src() -> str | None:
    env = os.environ.get("AICHALLENGE_MCP_SRC", "").strip()
    if env:
        return env
    sibling = Path(__file__).resolve().parents[3] / "AIChallenge" / "apps" / "mcp" / "src"
    if sibling.is_dir():
        return str(sibling)
    return None


async def _with_http(url: str, token: str, op):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers) as (read, write, _sid):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await op(session)


async def _with_stdio(op):
    src = _mcp_src()
    env = {**os.environ, "MCP_TRANSPORT": "stdio"}
    if src:
        env["PYTHONPATH"] = src
    params = StdioServerParameters(
        command=os.environ.get("PULSE_STDIO_CMD", sys.executable),
        args=["-m", "aichallenge_mcp"],
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await op(session)


async def cmd_list(session: ClientSession) -> int:
    listed = await session.list_tools()
    print(f"{'name':<18} description")
    print(f"{'-' * 18} {'-' * 52}")
    for tool in listed.tools:
        print(f"{tool.name:<18} {(tool.description or '').strip()}")
    return 0


async def cmd_call(session: ClientSession, name: str, arguments: dict[str, Any]) -> int:
    result = await session.call_tool(name, arguments)
    raw = _text(result)
    if name == "watch_brief":
        print(format_watch(_parse_json(raw)))
    else:
        print(_pretty(raw))
    return 1 if getattr(result, "isError", False) else 0


def _parse_args(pairs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in pairs:
        if "=" not in item:
            raise SystemExit(f"argument must be key=value, got {item!r}")
        key, value = item.split("=", 1)
        if value.isdigit():
            out[key] = int(value)
        else:
            out[key] = value
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pulse",
        description="On-call client for Stand Pulse: watch incidents, probe the stand, schedule digests.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Streamable HTTP MCP URL")
    parser.add_argument(
        "--token",
        default=os.environ.get("MCP_SHARED_TOKEN", ""),
        help="Bearer token (or env MCP_SHARED_TOKEN). Never commit the value.",
    )
    parser.add_argument("--stdio", action="store_true", help="local stdio MCP instead of HTTP")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="initialize + list_tools")
    sub.add_parser("watch", help="on-call brief: severity and open incidents")
    call = sub.add_parser("call", help="call a tool by name")
    call.add_argument("name")
    call.add_argument("kv", nargs="*", help="arguments as key=value")
    sub.add_parser("probe", help="shortcut for call probe_stand")
    sub.add_parser("digest", help="latest aggregated digest")
    sub.add_parser("history", help="recent /health probes")
    schedule = sub.add_parser("schedule", help="start a recurring digest")
    schedule.add_argument("--every", type=int, default=3600, help="interval seconds")
    schedule.add_argument("--hours", type=int, default=24)
    schedule.add_argument("--note", default="cli")
    sub.add_parser("jobs", help="list scheduled jobs")
    ack = sub.add_parser("ack", help="acknowledge an open incident")
    ack.add_argument("incident_id")
    ack.add_argument("--note", default="acked from cli")
    return parser


async def run(args: argparse.Namespace) -> int:
    async def op(session: ClientSession) -> int:
        if args.cmd == "list":
            return await cmd_list(session)
        if args.cmd == "watch":
            return await cmd_call(session, "watch_brief", {})
        if args.cmd == "probe":
            return await cmd_call(session, "probe_stand", {})
        if args.cmd == "digest":
            return await cmd_call(session, "latest_digest", {})
        if args.cmd == "history":
            return await cmd_call(session, "probe_history", {"limit": 8})
        if args.cmd == "jobs":
            return await cmd_call(session, "list_jobs", {})
        if args.cmd == "ack":
            return await cmd_call(
                session,
                "ack_incident",
                {"incident_id": args.incident_id, "note": args.note},
            )
        if args.cmd == "schedule":
            return await cmd_call(
                session,
                "schedule_digest",
                {
                    "interval_seconds": args.every,
                    "hours": args.hours,
                    "note": args.note,
                },
            )
        if args.cmd == "call":
            return await cmd_call(session, args.name, _parse_args(args.kv))
        raise SystemExit(f"unknown command {args.cmd}")

    if args.stdio:
        return await _with_stdio(op)
    if not args.token:
        print("MCP_SHARED_TOKEN is empty. Pass --token or --stdio.", file=sys.stderr)
        return 2
    return await _with_http(args.url, args.token, op)


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
