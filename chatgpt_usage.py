#!/usr/bin/env python3
"""Local ChatGPT/Codex token usage meter.

Reads Codex Desktop/CLI JSONL session logs. It never uploads conversation data and
does not require an OpenAI API key.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import locale
import io
import json
import mimetypes
import os
import re
import sys
import time
import unicodedata
import webbrowser
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, TextIO
from urllib.parse import parse_qs, urlparse


APP_NAME = "ChatGPT / Codex Token Meter"
VERSION = "1.2.0"
DEFAULT_PRICES = Path(__file__).with_name("prices.json")
WEB_ROOT = Path(__file__).with_name("web")

TEXT = {
    "zh-TW": {
        "all_records": "全部本機紀錄",
        "period": "期間",
        "local_timezone": "本機時區",
        "source": "來源",
        "daily": "每日統計",
        "models": "模型統計",
        "date": "日期",
        "model": "模型",
        "events": "計數事件",
        "input": "輸入",
        "cached": "快取",
        "cache_write": "快取寫入",
        "output": "輸出",
        "reasoning": "推理輸出",
        "total_tokens": "總 token",
        "api_equivalent": "API 等值（USD）",
        "no_records": "（這段期間沒有找到 token 使用紀錄）",
        "no_data": "（無資料）",
        "total": "合計",
        "scan_summary": "掃描 {files:,} 個工作階段檔；去除 {duplicates:,} 個重複快照；價格表更新日 {updated}。",
        "cost_note": "API 等值只估算文字 token，不含工具呼叫、圖片、影片、語音或其他費用。",
        "unpriced": "* 部分成本未計價（{models}）；可在 prices.json 補上價格。",
        "malformed": "提示：略過 {count:,} 行未完成／無法解析的即時紀錄。",
        "unreadable": "警告：有 {count} 個檔案無法讀取。",
        "description": "統計 Codex Desktop/CLI 的本機 token 使用量與 API 等值成本。",
        "help_date": "指定日期（YYYY-MM-DD）",
        "help_all": "統計全部本機紀錄",
        "help_days": "含今天往回 N 天（預設：1）",
        "help_home": "Codex 資料目錄（預設：CODEX_HOME 或 ~/.codex）",
        "help_prices": "自訂 prices.json",
        "help_json": "輸出 JSON",
        "help_watch": "每隔指定秒數重新整理（建議 5 秒以上）",
        "help_lang": "介面語言（預設：依系統自動判斷）",
        "help_web": "啟動本機網頁儀表板",
        "help_port": "網頁儀表板連接埠（預設：8765）",
        "help_no_browser": "啟動網頁伺服器但不自動開啟瀏覽器",
        "invalid_days": "--days 必須大於或等於 1",
        "missing_home": "找不到 Codex 資料目錄：{path}",
        "invalid_watch": "--watch 必須至少為 1 秒",
        "watch_json": "--watch 不能和 --json 同時使用",
        "web_watch": "--web 不能和 --watch 或 --json 同時使用",
        "scanning": "正在掃描本機工作階段，請稍候…",
        "watching": "每 {seconds:g} 秒重新整理；按 Ctrl+C 結束。",
        "error": "錯誤",
        "web_ready": "本機儀表板已啟動：{url}",
        "web_stop": "按 Ctrl+C 關閉。資料只在這台電腦上處理。",
    },
    "en": {
        "all_records": "All local records",
        "period": "Period",
        "local_timezone": "local time zone",
        "source": "Source",
        "daily": "Daily usage",
        "models": "Usage by model",
        "date": "Date",
        "model": "Model",
        "events": "Events",
        "input": "Input",
        "cached": "Cached",
        "cache_write": "Cache write",
        "output": "Output",
        "reasoning": "Reasoning",
        "total_tokens": "Total tokens",
        "api_equivalent": "API equivalent (USD)",
        "no_records": "(No token usage records found for this period.)",
        "no_data": "(No data)",
        "total": "Total",
        "scan_summary": "Scanned {files:,} session files; removed {duplicates:,} duplicate snapshots; pricing updated {updated}.",
        "cost_note": "API equivalent estimates text tokens only; tool calls, images, video, audio, storage, and other charges are excluded.",
        "unpriced": "* Some models are unpriced ({models}); add their rates to prices.json.",
        "malformed": "Note: skipped {count:,} incomplete or malformed live-log lines.",
        "unreadable": "Warning: {count} files could not be read.",
        "description": "Report local Codex Desktop/CLI token usage and API-equivalent cost.",
        "help_date": "Report one date (YYYY-MM-DD)",
        "help_all": "Report all local history",
        "help_days": "Include today and the previous N-1 days (default: 1)",
        "help_home": "Codex data directory (default: CODEX_HOME or ~/.codex)",
        "help_prices": "Custom prices.json path",
        "help_json": "Output JSON",
        "help_watch": "Refresh every N seconds (5 or more recommended)",
        "help_lang": "Interface language (default: auto-detect)",
        "help_web": "Start the local web dashboard",
        "help_port": "Web dashboard port (default: 8765)",
        "help_no_browser": "Start the web server without opening a browser",
        "invalid_days": "--days must be at least 1",
        "missing_home": "Codex data directory not found: {path}",
        "invalid_watch": "--watch must be at least 1 second",
        "watch_json": "--watch cannot be combined with --json",
        "web_watch": "--web cannot be combined with --watch or --json",
        "scanning": "Scanning local sessions. Please wait…",
        "watching": "Refreshing every {seconds:g} seconds; press Ctrl+C to stop.",
        "error": "Error",
        "web_ready": "Local dashboard is running at {url}",
        "web_stop": "Press Ctrl+C to stop. Data is processed only on this computer.",
    },
}


def normalize_language(value: str | None) -> str:
    if value and value != "auto":
        return "zh-TW" if value.lower() in {"zh", "zh-tw", "zh_hant"} else "en"
    system_locale = (locale.getlocale()[0] or "").lower()
    return "zh-TW" if system_locale.startswith("zh") else "en"


def language_from_argv(argv: list[str]) -> str:
    for index, item in enumerate(argv):
        if item.startswith("--lang="):
            return normalize_language(item.split("=", 1)[1])
        if item == "--lang" and index + 1 < len(argv):
            return normalize_language(argv[index + 1])
    return normalize_language("auto")


def tr(lang: str, key: str, **values: Any) -> str:
    template = TEXT.get(lang, TEXT["en"]).get(key, key)
    return template.format(**values)


@dataclass(frozen=True)
class TokenSnapshot:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_payload(cls, value: dict[str, Any]) -> "TokenSnapshot":
        def number(*names: str) -> int:
            for name in names:
                raw = value.get(name)
                if isinstance(raw, (int, float)) and raw >= 0:
                    return int(raw)
            return 0

        input_tokens = number("input_tokens", "prompt_tokens")
        output_tokens = number("output_tokens", "completion_tokens")
        return cls(
            input_tokens=input_tokens,
            cached_input_tokens=number(
                "cached_input_tokens", "input_cached_tokens", "cached_tokens"
            ),
            cache_write_input_tokens=number(
                "cache_write_input_tokens", "input_cache_write_tokens"
            ),
            output_tokens=output_tokens,
            reasoning_output_tokens=number(
                "reasoning_output_tokens", "output_reasoning_tokens", "reasoning_tokens"
            ),
            total_tokens=number("total_tokens") or input_tokens + output_tokens,
        )

    def values(self) -> tuple[int, ...]:
        return (
            self.input_tokens,
            self.cached_input_tokens,
            self.cache_write_input_tokens,
            self.output_tokens,
            self.reasoning_output_tokens,
            self.total_tokens,
        )

    def delta_from(self, previous: "TokenSnapshot | None") -> "TokenSnapshot":
        if previous is None:
            return self
        current_values = self.values()
        previous_values = previous.values()
        if all(current >= old for current, old in zip(current_values, previous_values)):
            differences = [
                current - old for current, old in zip(current_values, previous_values)
            ]
            return TokenSnapshot(*differences)
        # A counter reset can happen after a resumed/imported session. Treat the new
        # snapshot as a fresh baseline rather than producing negative usage.
        return self


@dataclass(frozen=True)
class RawUsageEvent:
    session_id: str
    timestamp: datetime
    model: str
    cumulative_snapshot: TokenSnapshot
    last_usage: TokenSnapshot | None


@dataclass(frozen=True)
class UsageRecord:
    session_id: str
    timestamp: datetime
    model: str
    tokens: TokenSnapshot
    api_equivalent_usd: float | None


@dataclass
class ScanDiagnostics:
    files: int = 0
    parsed_lines: int = 0
    malformed_lines: int = 0
    token_events: int = 0
    duplicate_snapshots: int = 0
    counter_resets: int = 0
    unreadable_files: list[str] = field(default_factory=list)


@dataclass
class Aggregate:
    requests: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0
    known_cost_usd: float = 0.0
    unpriced_requests: int = 0
    unpriced_tokens: int = 0

    def add(self, record: UsageRecord) -> None:
        self.requests += 1
        self.input_tokens += record.tokens.input_tokens
        self.cached_input_tokens += record.tokens.cached_input_tokens
        self.cache_write_input_tokens += record.tokens.cache_write_input_tokens
        self.output_tokens += record.tokens.output_tokens
        self.reasoning_output_tokens += record.tokens.reasoning_output_tokens
        self.total_tokens += record.tokens.total_tokens
        if record.api_equivalent_usd is None:
            self.unpriced_requests += 1
            self.unpriced_tokens += record.tokens.total_tokens
        else:
            self.known_cost_usd += record.api_equivalent_usd


class PriceCatalog:
    def __init__(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"Price file not found / 找不到價格檔：{path}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read price file / 無法讀取價格檔 {path}: {exc}") from exc

        self.path = path
        self.updated = str(data.get("updated", "unknown"))
        self.per_tokens = int(data.get("per_tokens", 1_000_000))
        self.models: dict[str, dict[str, Any]] = data.get("models", {})
        if self.per_tokens <= 0 or not isinstance(self.models, dict):
            raise ValueError(f"Invalid price file / 價格檔格式錯誤：{path}")

    def find(self, model: str) -> dict[str, Any] | None:
        candidate = model.lower().strip()
        if candidate in self.models:
            return self.models[candidate]
        for canonical, details in self.models.items():
            aliases = [str(item).lower() for item in details.get("aliases", [])]
            prefixes = [str(item).lower() for item in details.get("prefixes", [])]
            if candidate in aliases or any(candidate.startswith(prefix) for prefix in prefixes):
                return details
            if candidate == canonical.lower():
                return details
        return None

    def estimate(self, model: str, tokens: TokenSnapshot) -> float | None:
        price = self.find(model)
        if price is None:
            return None

        cached = min(tokens.cached_input_tokens, tokens.input_tokens)
        remaining = max(tokens.input_tokens - cached, 0)
        cache_write = min(tokens.cache_write_input_tokens, remaining)
        uncached = max(remaining - cache_write, 0)

        input_multiplier = 1.0
        output_multiplier = 1.0
        threshold = price.get("long_context_threshold")
        if isinstance(threshold, int) and tokens.input_tokens > threshold:
            input_multiplier = float(price.get("long_context_input_multiplier", 1.0))
            output_multiplier = float(price.get("long_context_output_multiplier", 1.0))

        input_cost = (
            uncached * float(price["input"])
            + cached * float(price.get("cached_input", price["input"]))
            + cache_write * float(price.get("cache_write_input", price["input"]))
        ) * input_multiplier
        output_cost = (
            tokens.output_tokens * float(price["output"]) * output_multiplier
        )
        return (input_cost + output_cost) / self.per_tokens


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass


def open_shared_text(path: Path) -> TextIO:
    """Open a live JSONL file while Codex Desktop is appending on Windows."""
    if os.name != "nt":
        return path.open("r", encoding="utf-8", errors="replace")

    from ctypes import wintypes
    import msvcrt

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        str(path),
        0x80000000,  # GENERIC_READ
        0x00000001 | 0x00000002 | 0x00000004,  # share read/write/delete
        None,
        3,  # OPEN_EXISTING
        0x00000080,  # FILE_ATTRIBUTE_NORMAL
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        raise ctypes.WinError()
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY)
    except Exception:
        kernel32.CloseHandle(handle)
        raise
    binary = os.fdopen(descriptor, "rb", closefd=True)
    return io.TextIOWrapper(binary, encoding="utf-8", errors="replace", newline="")


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def session_start_from_name(path: Path, local_tz: Any) -> datetime | None:
    match = re.search(
        r"rollout-(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})", path.name
    )
    if not match:
        return None
    try:
        parsed = datetime.strptime(match.group(1), "%Y-%m-%dT%H-%M-%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=local_tz)


def is_probably_live_file(path: Path) -> bool:
    """Return True when a Windows writer is holding a rollout file open.

    Windows may defer LastWriteTime updates until the writer closes its handle, so
    mtime alone can exclude a resumed task that is producing tokens right now.
    """
    if os.name != "nt":
        return False
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    ctypes.set_last_error(0)
    handle = create_file(
        str(path),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ only; an active append handle conflicts
        None,
        3,
        0x00000080,
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle != invalid_handle:
        kernel32.CloseHandle(handle)
        return False
    return ctypes.get_last_error() == 32  # ERROR_SHARING_VIOLATION


def discover_session_files(
    codex_home: Path, start: datetime | None, end: datetime | None
) -> list[Path]:
    paths: list[Path] = []
    for directory_name in ("sessions", "archived_sessions"):
        directory = codex_home / directory_name
        if directory.is_dir():
            paths.extend(directory.rglob("*.jsonl"))
    unique_paths = sorted(set(paths))
    if start is None and end is None:
        return unique_paths

    candidates: list[Path] = []
    for path in unique_paths:
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
        except OSError:
            candidates.append(path)
            continue
        # A file cannot contain an event after its last modification time.
        if start is not None and modified < start and not is_probably_live_file(path):
            continue
        # The rollout filename is generated in local time. A session that started
        # after the selected range cannot contain an earlier event.
        rollout_start = session_start_from_name(path, modified.tzinfo)
        if end is not None and rollout_start is not None and rollout_start >= end:
            continue
        candidates.append(path)
    return candidates


def load_raw_events(
    files: Iterable[Path], diagnostics: ScanDiagnostics
) -> dict[str, list[RawUsageEvent]]:
    sessions: dict[str, list[RawUsageEvent]] = defaultdict(list)
    for path in files:
        diagnostics.files += 1
        session_id = path.stem
        current_model = "unknown"
        try:
            stream = open_shared_text(path)
        except OSError:
            diagnostics.unreadable_files.append(str(path))
            continue

        with stream:
            for line in stream:
                diagnostics.parsed_lines += 1
                # Most JSONL lines contain messages or tool output and can be very
                # large. Avoid decoding chat content; only parse the three small
                # event types needed for metering.
                if not any(
                    marker in line
                    for marker in (
                        '"type":"session_meta"',
                        '"type":"turn_context"',
                        '"type":"token_count"',
                    )
                ):
                    continue
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    diagnostics.malformed_lines += 1
                    continue

                event_type = event.get("type")
                payload = event.get("payload")
                if not isinstance(payload, dict):
                    continue
                if event_type == "session_meta":
                    raw_id = payload.get("id")
                    if isinstance(raw_id, str) and raw_id:
                        session_id = raw_id
                    continue
                if event_type == "turn_context":
                    raw_model = payload.get("model")
                    if isinstance(raw_model, str) and raw_model:
                        current_model = raw_model
                    continue
                if event_type != "event_msg" or payload.get("type") != "token_count":
                    continue

                info = payload.get("info")
                if not isinstance(info, dict):
                    continue
                total_usage = info.get("total_token_usage")
                last_usage = info.get("last_token_usage")
                timestamp = parse_timestamp(event.get("timestamp"))
                if not isinstance(total_usage, dict) or timestamp is None:
                    continue
                cumulative_snapshot = TokenSnapshot.from_payload(total_usage)
                if cumulative_snapshot.total_tokens <= 0:
                    continue
                sessions[session_id].append(
                    RawUsageEvent(
                        session_id=session_id,
                        timestamp=timestamp,
                        model=current_model,
                        cumulative_snapshot=cumulative_snapshot,
                        last_usage=(
                            TokenSnapshot.from_payload(last_usage)
                            if isinstance(last_usage, dict)
                            else None
                        ),
                    )
                )
                diagnostics.token_events += 1
    return sessions


def calculate_records(
    sessions: dict[str, list[RawUsageEvent]],
    catalog: PriceCatalog,
    diagnostics: ScanDiagnostics,
) -> list[UsageRecord]:
    records: list[UsageRecord] = []
    for session_id, events in sessions.items():
        previous: TokenSnapshot | None = None
        seen_snapshots: set[tuple[int, ...]] = set()
        for event in sorted(events, key=lambda item: item.timestamp):
            values = event.cumulative_snapshot.values()
            # Codex can write the same token event more than once (for example when
            # only rate-limit metadata changes), and copied/resumed logs can repeat
            # an earlier cumulative snapshot.
            if values in seen_snapshots:
                diagnostics.duplicate_snapshots += 1
                continue
            seen_snapshots.add(values)
            if previous is not None and any(
                current < old
                for current, old in zip(event.cumulative_snapshot.values(), previous.values())
            ):
                diagnostics.counter_resets += 1
            # last_token_usage is the server-provided increment for this event and
            # stays correct across branching/resume counter resets. Older logs may
            # omit it, so retain cumulative differencing as a compatibility fallback.
            usage = event.last_usage or event.cumulative_snapshot.delta_from(previous)
            previous = event.cumulative_snapshot
            if usage.total_tokens <= 0:
                continue
            records.append(
                UsageRecord(
                    session_id=session_id,
                    timestamp=event.timestamp,
                    model=event.model or "unknown",
                    tokens=usage,
                    api_equivalent_usd=catalog.estimate(event.model, usage),
                )
            )
    return sorted(records, key=lambda item: item.timestamp)


def aggregate_by(records: Iterable[UsageRecord], key_name: str) -> dict[str, Aggregate]:
    groups: dict[str, Aggregate] = defaultdict(Aggregate)
    for record in records:
        if key_name == "model":
            key = record.model
        elif key_name == "date":
            key = record.timestamp.astimezone().date().isoformat()
        else:
            raise ValueError(f"unsupported aggregate key: {key_name}")
        groups[key].add(record)
    return dict(groups)


def display_width(value: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        for char in value
    )


def pad(value: str, width: int, right_align: bool = False) -> str:
    spaces = max(width - display_width(value), 0)
    return (" " * spaces + value) if right_align else (value + " " * spaces)


def render_table(headers: list[str], rows: list[list[str]], numeric_from: int = 1) -> str:
    widths = [display_width(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], display_width(value))

    def render_row(row: list[str]) -> str:
        return "  ".join(
            pad(value, widths[index], right_align=index >= numeric_from)
            for index, value in enumerate(row)
        ).rstrip()

    separator = "  ".join("─" * width for width in widths)
    return "\n".join([render_row(headers), separator, *(render_row(row) for row in rows)])


def format_tokens(value: int) -> str:
    return f"{value:,}"


def format_cost(aggregate: Aggregate) -> str:
    if aggregate.requests and aggregate.unpriced_requests == aggregate.requests:
        return "—"
    marker = "*" if aggregate.unpriced_requests else ""
    return f"${aggregate.known_cost_usd:,.6f}{marker}"


def aggregate_row(label: str, aggregate: Aggregate) -> list[str]:
    return [
        label,
        format_tokens(aggregate.requests),
        format_tokens(aggregate.input_tokens),
        format_tokens(aggregate.cached_input_tokens),
        format_tokens(aggregate.cache_write_input_tokens),
        format_tokens(aggregate.output_tokens),
        format_tokens(aggregate.reasoning_output_tokens),
        format_tokens(aggregate.total_tokens),
        format_cost(aggregate),
    ]


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Date must use YYYY-MM-DD / 日期格式必須是 YYYY-MM-DD"
        ) from exc


def selected_range(args: argparse.Namespace) -> tuple[datetime | None, datetime | None, str]:
    local_tz = datetime.now().astimezone().tzinfo
    if args.all:
        return None, None, tr(args.lang, "all_records")
    target = args.date or datetime.now().astimezone().date()
    days = 1 if args.date else args.days
    start_date = target - timedelta(days=days - 1)
    start = datetime.combine(start_date, datetime_time.min, tzinfo=local_tz)
    end = datetime.combine(target + timedelta(days=1), datetime_time.min, tzinfo=local_tz)
    if days == 1:
        label = target.isoformat()
    else:
        label = f"{start_date.isoformat()} ～ {target.isoformat()}"
    return start, end, label


def filter_records(
    records: Iterable[UsageRecord], start: datetime | None, end: datetime | None
) -> list[UsageRecord]:
    selected: list[UsageRecord] = []
    for record in records:
        local_timestamp = record.timestamp.astimezone()
        if start is not None and local_timestamp < start:
            continue
        if end is not None and local_timestamp >= end:
            continue
        selected.append(record)
    return selected


def text_report(
    records: list[UsageRecord],
    diagnostics: ScanDiagnostics,
    codex_home: Path,
    catalog: PriceCatalog,
    period_label: str,
    lang: str,
) -> str:
    daily = aggregate_by(records, "date")
    models = aggregate_by(records, "model")
    total = Aggregate()
    for record in records:
        total.add(record)

    output = [
        APP_NAME,
        f"{tr(lang, 'period')}: {period_label} ({tr(lang, 'local_timezone')}: {datetime.now().astimezone().tzname()})",
        f"{tr(lang, 'source')}: {codex_home}",
        "",
        tr(lang, "daily"),
    ]
    daily_headers = [
        tr(lang, "date"),
        tr(lang, "events"),
        tr(lang, "input"),
        tr(lang, "cached"),
        tr(lang, "cache_write"),
        tr(lang, "output"),
        tr(lang, "reasoning"),
        tr(lang, "total_tokens"),
        tr(lang, "api_equivalent"),
    ]
    daily_rows = [
        aggregate_row(day, aggregate)
        for day, aggregate in sorted(daily.items())
    ]
    if daily_rows:
        output.append(render_table(daily_headers, daily_rows))
    else:
        output.append(tr(lang, "no_records"))

    output.extend(["", tr(lang, "models")])
    model_rows = [
        aggregate_row(model, aggregate)
        for model, aggregate in sorted(
            models.items(), key=lambda item: item[1].total_tokens, reverse=True
        )
    ]
    if model_rows:
        model_rows.append(aggregate_row(tr(lang, "total"), total))
        model_headers = daily_headers.copy()
        model_headers[0] = tr(lang, "model")
        output.append(render_table(model_headers, model_rows))
    else:
        output.append(tr(lang, "no_data"))

    output.extend(
        [
            "",
            tr(
                lang,
                "scan_summary",
                files=diagnostics.files,
                duplicates=diagnostics.duplicate_snapshots,
                updated=catalog.updated,
            ),
            tr(lang, "cost_note"),
        ]
    )
    if total.unpriced_requests:
        names = sorted(
            model for model, aggregate in models.items() if aggregate.unpriced_requests
        )
        output.append(tr(lang, "unpriced", models=", ".join(names)))
    if diagnostics.malformed_lines:
        output.append(tr(lang, "malformed", count=diagnostics.malformed_lines))
    if diagnostics.unreadable_files:
        output.append(tr(lang, "unreadable", count=len(diagnostics.unreadable_files)))
    return "\n".join(output)


def report_payload(
    records: list[UsageRecord],
    diagnostics: ScanDiagnostics,
    codex_home: Path,
    catalog: PriceCatalog,
    period_label: str,
) -> dict[str, Any]:
    daily = aggregate_by(records, "date")
    models = aggregate_by(records, "model")
    total = Aggregate()
    for record in records:
        total.add(record)
    return {
        "app": APP_NAME,
        "version": VERSION,
        "period": period_label,
        "local_timezone": datetime.now().astimezone().tzname(),
        "source": str(codex_home),
        "currency": "USD",
        "pricing_updated": catalog.updated,
        "daily": {key: asdict(value) for key, value in sorted(daily.items())},
        "models": {key: asdict(value) for key, value in sorted(models.items())},
        "total": asdict(total),
        "diagnostics": asdict(diagnostics),
    }


def json_report(
    records: list[UsageRecord],
    diagnostics: ScanDiagnostics,
    codex_home: Path,
    catalog: PriceCatalog,
    period_label: str,
) -> str:
    return json.dumps(
        report_payload(records, diagnostics, codex_home, catalog, period_label),
        ensure_ascii=False,
        indent=2,
    )


def build_parser(lang: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=tr(lang, "description")
    )
    range_group = parser.add_mutually_exclusive_group()
    range_group.add_argument("--date", type=parse_date, help=tr(lang, "help_date"))
    range_group.add_argument("--all", action="store_true", help=tr(lang, "help_all"))
    parser.add_argument(
        "--days", type=int, default=1, help=tr(lang, "help_days")
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help=tr(lang, "help_home"),
    )
    parser.add_argument(
        "--prices", type=Path, default=DEFAULT_PRICES, help=tr(lang, "help_prices")
    )
    parser.add_argument("--json", action="store_true", help=tr(lang, "help_json"))
    parser.add_argument(
        "--watch",
        type=float,
        metavar="SECONDS",
        help=tr(lang, "help_watch"),
    )
    parser.add_argument(
        "--lang",
        choices=("auto", "en", "zh-TW"),
        default="auto",
        help=tr(lang, "help_lang"),
    )
    parser.add_argument("--web", action="store_true", help=tr(lang, "help_web"))
    parser.add_argument("--port", type=int, default=8765, help=tr(lang, "help_port"))
    parser.add_argument(
        "--no-browser", action="store_true", help=tr(lang, "help_no_browser")
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def collect_report(
    args: argparse.Namespace,
) -> tuple[list[UsageRecord], ScanDiagnostics, Path, PriceCatalog, str]:
    if args.days < 1:
        raise ValueError(tr(args.lang, "invalid_days"))
    codex_home = args.codex_home.expanduser().resolve()
    if not codex_home.is_dir():
        raise ValueError(tr(args.lang, "missing_home", path=codex_home))

    catalog = PriceCatalog(args.prices.expanduser().resolve())
    diagnostics = ScanDiagnostics()
    start, end, period_label = selected_range(args)
    files = discover_session_files(codex_home, start, end)
    sessions = load_raw_events(files, diagnostics)
    all_records = calculate_records(sessions, catalog, diagnostics)
    records = filter_records(all_records, start, end)
    return records, diagnostics, codex_home, catalog, period_label


def generate(args: argparse.Namespace) -> str:
    records, diagnostics, codex_home, catalog, period_label = collect_report(args)
    if args.json:
        return json_report(records, diagnostics, codex_home, catalog, period_label)
    return text_report(
        records,
        diagnostics,
        codex_home,
        catalog,
        period_label,
        args.lang,
    )


def query_argument(query: dict[str, list[str]], name: str) -> str | None:
    values = query.get(name)
    return values[0] if values else None


def web_report_args(base_args: argparse.Namespace, query: dict[str, list[str]]) -> argparse.Namespace:
    args = copy.copy(base_args)
    args.web = False
    args.watch = None
    args.json = False
    args.all = query_argument(query, "all") == "1"
    raw_date = query_argument(query, "date")
    args.date = parse_date(raw_date) if raw_date and not args.all else None
    raw_days = query_argument(query, "days")
    args.days = int(raw_days) if raw_days and not args.date and not args.all else 1
    args.lang = normalize_language(query_argument(query, "lang") or base_args.lang)
    return args


class DashboardHandler(BaseHTTPRequestHandler):
    base_args: argparse.Namespace
    web_root: Path
    cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_asset(self, relative_path: str) -> None:
        path = self.web_root / relative_path
        if not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        content_type, _ = mimetypes.guess_type(path.name)
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]").lower()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            self.send_error(403)
            return
        request = urlparse(self.path)
        if request.path == "/":
            self.send_asset("index.html")
            return
        assets = {"/app.js": "app.js", "/styles.css": "styles.css"}
        if request.path in assets:
            self.send_asset(assets[request.path])
            return
        if request.path == "/api/health":
            self.send_json({"ok": True, "version": VERSION})
            return
        if request.path != "/api/report":
            self.send_error(404)
            return

        try:
            query = parse_qs(request.query)
            args = web_report_args(self.base_args, query)
            cache_key = request.query or "default"
            cached = self.cache.get(cache_key)
            if cached and time.monotonic() - cached[0] < 5:
                self.send_json(cached[1])
                return
            records, diagnostics, codex_home, catalog, period_label = collect_report(args)
            payload = report_payload(
                records, diagnostics, codex_home, catalog, period_label
            )
            self.cache[cache_key] = (time.monotonic(), payload)
            self.send_json(payload)
        except (ValueError, argparse.ArgumentTypeError) as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:  # Keep the local dashboard responsive on bad logs.
            self.send_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_web_dashboard(args: argparse.Namespace) -> None:
    if not WEB_ROOT.is_dir():
        raise ValueError(f"Web assets not found / 找不到網頁檔案：{WEB_ROOT}")
    if not 1 <= args.port <= 65535:
        raise ValueError("--port must be between 1 and 65535")

    class BoundDashboardHandler(DashboardHandler):
        base_args = args
        web_root = WEB_ROOT

    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), BoundDashboardHandler)
    except OSError as exc:
        raise ValueError(f"Unable to start localhost:{args.port}: {exc}") from exc
    url = f"http://127.0.0.1:{args.port}/"
    print(tr(args.lang, "web_ready", url=url), flush=True)
    print(tr(args.lang, "web_stop"), flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> int:
    configure_console()
    parser_lang = language_from_argv(sys.argv[1:])
    parser = build_parser(parser_lang)
    args = parser.parse_args()
    args.lang = normalize_language(args.lang) if args.lang != "auto" else parser_lang
    if args.watch is not None and args.watch < 1:
        parser.error(tr(args.lang, "invalid_watch"))
    if args.watch is not None and args.json:
        parser.error(tr(args.lang, "watch_json"))
    if args.web and (args.watch is not None or args.json):
        parser.error(tr(args.lang, "web_watch"))

    try:
        if args.web:
            run_web_dashboard(args)
            return 0
        while True:
            if args.watch is not None:
                os.system("cls" if os.name == "nt" else "clear")
            print(tr(args.lang, "scanning"), file=sys.stderr, flush=True)
            report = generate(args)
            print(report)
            if args.watch is None:
                break
            print("\n" + tr(args.lang, "watching", seconds=args.watch))
            time.sleep(args.watch)
    except KeyboardInterrupt:
        return 130
    except ValueError as exc:
        print(f"{tr(args.lang, 'error')}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
