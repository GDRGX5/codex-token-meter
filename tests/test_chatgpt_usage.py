import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "chatgpt_usage.py"
SPEC = importlib.util.spec_from_file_location("chatgpt_usage", MODULE_PATH)
meter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = meter
SPEC.loader.exec_module(meter)


class MeterTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.codex_home = Path(self.temp_dir.name)
        self.session_dir = self.codex_home / "sessions" / "2026" / "08" / "30"
        self.session_dir.mkdir(parents=True)
        self.catalog = meter.PriceCatalog(MODULE_PATH.with_name("prices.json"))

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def token_event(timestamp, total, last):
        return {
            "timestamp": timestamp,
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"total_token_usage": total, "last_token_usage": last},
            },
        }

    def write_fixture(self):
        first = {
            "input_tokens": 100,
            "cached_input_tokens": 40,
            "output_tokens": 20,
            "reasoning_output_tokens": 5,
            "total_tokens": 120,
        }
        second_total = {
            "input_tokens": 250,
            "cached_input_tokens": 100,
            "output_tokens": 30,
            "reasoning_output_tokens": 8,
            "total_tokens": 280,
        }
        second_last = {
            "input_tokens": 150,
            "cached_input_tokens": 60,
            "output_tokens": 10,
            "reasoning_output_tokens": 3,
            "total_tokens": 160,
        }
        reset = {
            "input_tokens": 50,
            "cached_input_tokens": 0,
            "output_tokens": 5,
            "reasoning_output_tokens": 0,
            "total_tokens": 55,
        }
        events = [
            {
                "timestamp": "2026-08-30T02:00:00Z",
                "type": "session_meta",
                "payload": {"id": "session-1"},
            },
            {
                "timestamp": "2026-08-30T02:00:01Z",
                "type": "turn_context",
                "payload": {"model": "gpt-5.6-sol"},
            },
            self.token_event("2026-08-30T02:00:02Z", first, first),
            self.token_event("2026-08-30T02:00:03Z", first, first),
            self.token_event("2026-08-30T02:00:04Z", second_total, second_last),
            {
                "timestamp": "2026-08-30T02:00:05Z",
                "type": "turn_context",
                "payload": {"model": "gpt-5.6-terra"},
            },
            self.token_event("2026-08-30T02:00:06Z", reset, reset),
        ]
        path = self.session_dir / (
            "rollout-2026-08-30T10-00-00-00000000-0000-0000-0000-000000000001.jsonl"
        )
        path.write_text(
            "\n".join(json.dumps(event, separators=(",", ":")) for event in events),
            encoding="utf-8",
        )

    def records(self):
        diagnostics = meter.ScanDiagnostics()
        files = meter.discover_session_files(self.codex_home, None, None)
        sessions = meter.load_raw_events(files, diagnostics)
        return meter.calculate_records(sessions, self.catalog, diagnostics), diagnostics

    def test_deduplication_model_switch_and_counter_reset(self):
        self.write_fixture()
        records, diagnostics = self.records()
        self.assertEqual(len(records), 3)
        self.assertEqual(diagnostics.duplicate_snapshots, 1)
        self.assertEqual(diagnostics.counter_resets, 1)
        self.assertEqual(sum(item.tokens.input_tokens for item in records), 300)
        self.assertEqual(sum(item.tokens.output_tokens for item in records), 35)
        self.assertEqual(
            [item.model for item in records],
            ["gpt-5.6-sol", "gpt-5.6-sol", "gpt-5.6-terra"],
        )

    def test_cached_and_long_context_pricing(self):
        tokens = meter.TokenSnapshot(
            input_tokens=300_000,
            cached_input_tokens=200_000,
            output_tokens=10_000,
            total_tokens=310_000,
        )
        expected = (
            (100_000 * 4 + 200_000 * 0.4) * 2 + 10_000 * 20 * 1.5
        ) / 1_000_000
        self.assertAlmostEqual(self.catalog.estimate("gpt-5.6-sol", tokens), expected)

    def test_gpt_6_astra_pricing_and_snapshot_prefix(self):
        tokens = meter.TokenSnapshot(
            input_tokens=300_000,
            cached_input_tokens=100_000,
            cache_write_input_tokens=50_000,
            output_tokens=10_000,
            total_tokens=310_000,
        )
        expected = (
            (150_000 * 10 + 100_000 * 1 + 50_000 * 12.5) * 2
            + 10_000 * 50 * 1.5
        ) / 1_000_000
        self.assertAlmostEqual(
            self.catalog.estimate("gpt-6-astra-2026-09-01", tokens), expected
        )

    def test_new_sol_and_luna_pricing_boundary(self):
        # Include cached reads and writes; the surcharge starts above 272K.
        cases = [("gpt-6.1-sol", 2, 0.1, 2.5, 10),
                 ("gpt-6-sol", 2, 0.2, 2.5, 10),
                 ("gpt-6-luna", 0.1, 0.01, 0.125, 0.5)]
        for model, rate, cached, write, output in cases:
            for count in (272000, 272001):
                with self.subTest(model=model, input_tokens=count):
                    tokens = meter.TokenSnapshot(
                        input_tokens=count, cached_input_tokens=100000,
                        cache_write_input_tokens=50000, output_tokens=10000,
                    )
                    cost = (count - 150000) * rate + 100000 * cached + 50000 * write
                    expected = (cost * (2 if count > 272000 else 1)
                                + 10000 * output * (1.5 if count > 272000 else 1)) / 1000000
                    self.assertAlmostEqual(self.catalog.estimate(model, tokens), expected)
                    self.assertAlmostEqual(
                        self.catalog.estimate(model + "-2099-01-01", tokens), expected
                    )
        self.assertIsNone(self.catalog.find("gpt-6-unknown"))

    def test_english_and_chinese_text_reports(self):
        self.write_fixture()
        records, diagnostics = self.records()
        english = meter.text_report(
            records, diagnostics, self.codex_home, self.catalog, "test", "en"
        )
        chinese = meter.text_report(
            records, diagnostics, self.codex_home, self.catalog, "測試", "zh-TW"
        )
        self.assertIn("Daily usage", english)
        self.assertIn("Usage by model", english)
        self.assertIn("每日統計", chinese)
        self.assertIn("模型統計", chinese)

    def test_web_query_and_assets(self):
        base = argparse.Namespace(
            all=False,
            date=None,
            days=1,
            lang="en",
            web=True,
            watch=None,
            json=False,
        )
        args = meter.web_report_args(base, {"days": ["7"], "lang": ["zh-TW"]})
        self.assertEqual(args.days, 7)
        self.assertEqual(args.lang, "zh-TW")
        self.assertTrue((MODULE_PATH.parent / "web" / "index.html").is_file())
        self.assertTrue((MODULE_PATH.parent / "web" / "app.js").is_file())

    def test_unknown_model_is_unpriced(self):
        tokens = meter.TokenSnapshot(input_tokens=10, total_tokens=10)
        self.assertIsNone(self.catalog.estimate("unknown-model", tokens))

    def test_web_handler_ignores_client_disconnect(self):
        handler = object.__new__(meter.DashboardHandler)
        disconnects = (
            BrokenPipeError(),
            ConnectionAbortedError(10053, "client aborted the connection"),
            ConnectionResetError(10054, "client reset the connection"),
        )
        for error in disconnects:
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(
                    meter.BaseHTTPRequestHandler, "handle", side_effect=error
                ):
                    handler.handle()

    def test_web_handler_does_not_hide_server_errors(self):
        handler = object.__new__(meter.DashboardHandler)
        with mock.patch.object(
            meter.BaseHTTPRequestHandler,
            "handle",
            side_effect=RuntimeError("server bug"),
        ):
            with self.assertRaisesRegex(RuntimeError, "server bug"):
                handler.handle()


if __name__ == "__main__":
    unittest.main()
