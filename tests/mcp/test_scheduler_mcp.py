#!/usr/bin/env python3
"""Drive infra/mcp-servers/scheduler-mcp/server.py over stdio (JSON-RPC 2.0).

Run: python3 tests/mcp/test_scheduler_mcp.py   (exit code != 0 on failure)
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

SERVER = Path(__file__).resolve().parents[2] / "infra/mcp-servers/scheduler-mcp/server.py"
TOOL_NAMES = {"list_work_orders", "get_work_order_status", "get_machine_load",
              "find_bottlenecks", "get_capacity_summary"}


class Client:
    def __init__(self):
        self.p = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding="utf-8")
        self.n = 0

    def send_raw(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def request(self, method, params=None):
        self.n += 1
        msg = {"jsonrpc": "2.0", "id": self.n, "method": method}
        if params is not None:
            msg["params"] = params
        reply = self.send_raw(json.dumps(msg))
        assert reply["jsonrpc"] == "2.0" and reply["id"] == self.n, reply
        return reply

    def call(self, name, arguments=None):
        params = {"name": name}
        if arguments is not None:
            params["arguments"] = arguments
        return self.request("tools/call", params)

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=10)
        self.p.stdout.close()
        self.p.stderr.close()


def text_of(reply):
    content = reply["result"]["content"]
    assert len(content) == 1 and content[0]["type"] == "text", content
    return content[0]["text"]


class SchedulerMcpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = Client()

    @classmethod
    def tearDownClass(cls):
        cls.c.close()

    def ok_json(self, reply):
        self.assertNotIn("error", reply)
        self.assertIs(reply["result"]["isError"], False)
        return json.loads(text_of(reply))

    def tool_error(self, reply, fragment):
        self.assertNotIn("error", reply)
        self.assertIs(reply["result"]["isError"], True)
        self.assertIn(fragment, text_of(reply))
        self.assertNotIn("Traceback", text_of(reply))

    def test_00_initialize_and_list(self):
        r = self.c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                          "clientInfo": {"name": "t", "version": "0"}})
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", r["result"]["capabilities"])
        self.assertEqual(r["result"]["serverInfo"]["name"], "scheduler-mcp")
        # notification: no reply expected; the next reply must belong to ping
        self.c.p.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.assertEqual(self.c.request("ping")["result"], {})
        tools = self.c.request("tools/list")["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, TOOL_NAMES)
        for t in tools:
            self.assertTrue(t["description"])
            self.assertEqual(t["inputSchema"]["type"], "object")

    def test_list_work_orders(self):
        allw = self.ok_json(self.c.call("list_work_orders"))["work_orders"]
        self.assertGreaterEqual(len(allw), 2)
        sched = self.ok_json(self.c.call("list_work_orders", {"status": "scheduled"}))["work_orders"]
        self.assertTrue(sched and all(w["status"] == "scheduled" for w in sched))
        self.tool_error(self.c.call("list_work_orders", {"status": 5}), "must be of type string")

    def test_get_work_order_status(self):
        wo = self.ok_json(self.c.call("get_work_order_status", {"wo_id": "W2026042100123"}))
        self.assertEqual(wo["id"], "W2026042100123")
        self.tool_error(self.c.call("get_work_order_status", {}), "wo_id")
        self.tool_error(self.c.call("get_work_order_status", {"wo_id": "nope"}), "not found")

    def test_get_machine_load_honours_days_ahead(self):
        d7 = self.ok_json(self.c.call("get_machine_load", {"machine": "CNC#3"}))
        d14 = self.ok_json(self.c.call("get_machine_load", {"machine": "CNC#3", "days_ahead": 14}))
        self.assertEqual(d7["days_ahead"], 7)
        self.assertEqual(d14["days_ahead"], 14)
        self.assertAlmostEqual(d14["available_hours"], 2 * d7["available_hours"], places=1)
        self.assertEqual(d14["load_pct"], d7["load_pct"])
        self.tool_error(self.c.call("get_machine_load", {"machine": "CNC#3", "days_ahead": "7"}), "integer")
        self.tool_error(self.c.call("get_machine_load", {"machine": "CNC#3", "days_ahead": 0}), "between")
        self.tool_error(self.c.call("get_machine_load", {"machine": "X#9"}), "not found")

    def test_find_bottlenecks(self):
        b = self.ok_json(self.c.call("find_bottlenecks"))["bottlenecks"]
        self.assertTrue(b and all(m["load_pct"] >= 0.85 for m in b))
        none = self.ok_json(self.c.call("find_bottlenecks", {"threshold": 1}))["bottlenecks"]
        self.assertEqual(none, [])
        self.tool_error(self.c.call("find_bottlenecks", {"threshold": "high"}), "number")
        self.tool_error(self.c.call("find_bottlenecks", {"threshold": 0.5, "window_days": 7}), "unknown argument")

    def test_get_capacity_summary(self):
        s = self.ok_json(self.c.call("get_capacity_summary"))
        self.assertGreater(s["total_machines"], 0)
        self.assertTrue(s["as_of"].endswith("Z"))
        self.tool_error(self.c.call("get_capacity_summary", []), "must be an object")

    def test_protocol_errors(self):
        r = self.c.call("no_such_tool", {})
        self.assertEqual(r["error"]["code"], -32602)
        self.assertNotIn("result", r)
        self.assertEqual(self.c.request("no/such/method")["error"]["code"], -32601)
        self.assertEqual(self.c.send_raw("not json")["error"]["code"], -32700)
        self.assertEqual(self.c.send_raw("[1]")["error"]["code"], -32600)
        self.assertEqual(self.c.request("ping")["result"], {})  # still alive


class MissingDataTest(unittest.TestCase):
    def test_missing_mock_data_fails_loudly(self):
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "server.py"
            shutil.copy(SERVER, copy)  # no mock-data/ next to the copy
            r = subprocess.run([sys.executable, str(copy)], input="", capture_output=True,
                               text=True, timeout=10)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cannot load", r.stderr)
        self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
