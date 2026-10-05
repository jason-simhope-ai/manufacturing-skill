#!/usr/bin/env python3
"""Drive infra/mcp-servers/scheduler-mcp/server.py over stdio (JSON-RPC 2.0).

Run: python3 tests/mcp/test_scheduler_mcp.py   (exit code != 0 on failure)
"""
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

SERVER = Path(__file__).resolve().parents[2] / "infra/mcp-servers/scheduler-mcp/server.py"
SERVER_NAME = "manufacturing-scheduler"
REPO = Path(__file__).resolve().parents[2]
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
        self.assertEqual(r["result"]["serverInfo"]["name"], SERVER_NAME)
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

    def test_list_work_orders_filters_by_so_and_customer(self):
        by_so = self.ok_json(self.c.call("list_work_orders", {"so_id": "SO-2026-0425"}))
        self.assertTrue(by_so["work_orders"])
        self.assertTrue(all(w["so_id"] == "SO-2026-0425" for w in by_so["work_orders"]))
        by_cust = self.ok_json(self.c.call("list_work_orders", {"customer": "客戶A"}))
        self.assertEqual([w["so_id"] for w in by_cust["work_orders"]], ["SO-2026-0421"])
        self.assertEqual(self.ok_json(self.c.call("list_work_orders", {"so_id": "none"}))["work_orders"], [])

    def test_list_limit_default_max_and_has_more(self):
        full = self.ok_json(self.c.call("list_work_orders"))
        self.assertEqual((full["limit"], full["offset"]), (50, 0))
        self.assertIs(full["has_more"], False)
        self.assertEqual(full["returned"], full["total_matched"])
        page1 = self.ok_json(self.c.call("list_work_orders", {"limit": 3}))
        self.assertEqual((page1["returned"], page1["limit"]), (3, 3))
        self.assertIs(page1["has_more"], True)
        page2 = self.ok_json(self.c.call("list_work_orders", {"limit": 3, "offset": 3}))
        self.assertIs(page2["has_more"], False)
        ids = [w["id"] for w in page1["work_orders"] + page2["work_orders"]]
        self.assertEqual(ids, [w["id"] for w in full["work_orders"]])  # pages tile the list
        self.ok_json(self.c.call("list_work_orders", {"limit": 200}))  # max is accepted

    def test_list_limit_above_max_is_protocol_error(self):
        for tool in ("list_work_orders", "find_bottlenecks"):
            r = self.c.call(tool, {"limit": 201})
            self.assertEqual(r["error"]["code"], -32602, tool)
            self.assertIn("limit", r["error"]["message"])
            self.assertIn("200", r["error"]["message"])
            self.assertNotIn("unknown tool", r["error"]["message"])
        # other bad limits stay ordinary tool errors
        self.tool_error(self.c.call("list_work_orders", {"limit": 0}), "limit")
        self.tool_error(self.c.call("list_work_orders", {"limit": "5"}), "integer")
        self.tool_error(self.c.call("list_work_orders", {"offset": -1}), "offset")
        self.assertEqual(self.c.request("ping")["result"], {})

    def test_list_schemas_document_limit(self):
        tools = {t["name"]: t for t in self.c.request("tools/list")["result"]["tools"]}
        for name in ("list_work_orders", "find_bottlenecks"):
            limit = tools[name]["inputSchema"]["properties"]["limit"]
            self.assertEqual((limit["default"], limit["maximum"]), (50, 200))
            self.assertIn("has_more", tools[name]["description"])

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
        self.assertEqual([m["load_pct"] for m in b], sorted((m["load_pct"] for m in b), reverse=True))
        self.assertIs(self.ok_json(self.c.call("find_bottlenecks", {"limit": 1}))["has_more"], len(b) > 1)
        # threshold is inclusive: a machine exactly at the threshold is listed
        edge = self.ok_json(self.c.call("find_bottlenecks", {"threshold": 0.875}))["bottlenecks"]
        self.assertIn("Grinder#1", [m["machine"] for m in edge])
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
        self.assertIn("unknown tool", r["error"]["message"])
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


def load_server_module():
    spec = importlib.util.spec_from_file_location("scheduler_server_under_test", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ValidateTypesTest(unittest.TestCase):
    """validate() in-process: every JSON Schema type the server may declare."""

    @classmethod
    def setUpClass(cls):
        cls.m = load_server_module()

    def schema(self, spec, required=()):
        return self.m._schema({"x": spec}, required)

    def check(self, spec, value, expect_ok, fragment=""):
        problem = self.m.validate({"x": value}, self.schema(spec))
        if expect_ok:
            self.assertIsNone(problem, (spec, value))
        else:
            self.assertIsNotNone(problem, (spec, value))
            self.assertIn(fragment, problem)

    def test_boolean(self):
        self.check({"type": "boolean"}, True, True)
        self.check({"type": "boolean"}, False, True)
        for bad in (0, 1, "true", None):
            self.check({"type": "boolean"}, bad, False, "boolean")

    def test_array(self):
        spec = {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1, "maxItems": 2}
        self.check(spec, ["a"], True)
        self.check(spec, [], False, "at least 1")
        self.check(spec, ["a", "b", "c"], False, "at most 2")
        self.check(spec, ["a", 3], False, "x[1]")
        self.check(spec, ["a", ""], False, "x[1]")
        self.check(spec, "a", False, "array")
        self.check(spec, {"0": "a"}, False, "array")

    def test_object(self):
        spec = {"type": "object", "properties": {"n": {"type": "integer"}, "s": {"type": "string"}},
                "required": ["n"], "additionalProperties": False}
        self.check(spec, {"n": 1, "s": "z"}, True)
        self.check(spec, {"s": "z"}, False, "missing required argument: n in 'x'")
        self.check(spec, {"n": 1, "q": 1}, False, "unknown argument: q in 'x'")
        self.check(spec, {"n": "1"}, False, "x.n")
        self.check(spec, [1], False, "object")
        self.check({"type": "object"}, {"anything": [1]}, True)  # no properties declared

    def test_null(self):
        self.check({"type": "null"}, None, True)
        self.check({"type": "null"}, 0, False, "null")
        self.check({"type": "string"}, None, False, "string")

    def test_number_integer_and_bounds(self):
        self.check({"type": "integer"}, True, False, "integer")  # bool is not an int
        self.check({"type": "integer"}, 1.5, False, "integer")
        self.check({"type": "number"}, True, False, "number")
        self.check({"type": "number"}, float("nan"), False, "number")
        self.check({"type": "number", "minimum": 0}, -1, False, "at least 0")  # one-sided bound
        self.check({"type": "number", "maximum": 1}, 2, False, "at most 1")
        self.check({"type": "integer", "minimum": 1, "maximum": 3}, 4, False, "between 1 and 3")

    def test_unsupported_schema_type_is_a_bug_not_bad_input(self):
        with self.assertRaises(ValueError):
            self.m.validate({"x": 1}, self.schema({"type": "tuple"}))


class ErrorMappingTest(unittest.TestCase):
    """handle() in-process: server bugs are -32603, never 'unknown tool'."""

    @classmethod
    def setUpClass(cls):
        cls.m = load_server_module()
        cls.ds = cls.m.DataSource()

    def call(self, server, name, args):
        msg = {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
               "params": {"name": name, "arguments": args}}
        return server.handle(msg, self.ds)

    def test_validation_bug_is_internal_error_with_class_name(self):
        tools = {"broken": {"fn": lambda ds, a: {}, "description": "d",
                            "inputSchema": self.m._schema({"x": {"type": "tuple"}})}}
        server = self.m.McpServer({"name": "t", "version": "0"}, tools)
        r = self.call(server, "broken", {"x": 1})
        self.assertEqual(r["error"]["code"], -32603)
        self.assertIn("ValueError", r["error"]["message"])
        self.assertNotIn("unknown tool", r["error"]["message"])
        self.assertEqual(self.call(server, "nope", {})["error"]["code"], -32602)  # still distinct

    def test_malformed_schema_keyerror_is_not_unknown_tool(self):
        tools = {"typeless": {"fn": lambda ds, a: {}, "description": "d",
                              "inputSchema": self.m._schema({"x": {}})}}  # no "type" key
        server = self.m.McpServer({"name": "t", "version": "0"}, tools)
        r = self.call(server, "typeless", {"x": 1})
        self.assertEqual(r["error"]["code"], -32603)
        self.assertIn("KeyError", r["error"]["message"])

    def test_unserialisable_result_is_internal_error(self):
        tools = {"odd": {"fn": lambda ds, a: {"v": object()}, "description": "d",
                         "inputSchema": self.m._schema({})}}
        server = self.m.McpServer({"name": "t", "version": "0"}, tools)
        r = self.call(server, "odd", {})
        self.assertEqual(r["error"]["code"], -32603)
        self.assertIn("TypeError", r["error"]["message"])

    def test_tool_fn_exception_stays_a_tool_error(self):
        def boom(ds, a):
            raise RuntimeError("secret path /etc/x")
        tools = {"boom": {"fn": boom, "description": "d", "inputSchema": self.m._schema({})}}
        server = self.m.McpServer({"name": "t", "version": "0"}, tools)
        r = self.call(server, "boom", {})
        self.assertIs(r["result"]["isError"], True)
        self.assertNotIn("secret", json.dumps(r))

    def test_params_not_an_object_is_unknown_tool(self):
        server = self.m.build_server()
        r = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": 5}, self.ds)
        self.assertEqual(r["error"]["code"], -32602)

    def test_tool_with_all_new_types_end_to_end(self):
        seen = {}
        schema = self.m._schema({
            "flag": {"type": "boolean"},
            "fields": {"type": "array", "items": {"type": "string"}},
            "doc": {"type": "object", "properties": {"k": {"type": "integer"}}},
            "nothing": {"type": "null"}})
        tools = {"t": {"fn": lambda ds, a: seen.update(a) or a, "description": "d", "inputSchema": schema}}
        server = self.m.McpServer({"name": "t", "version": "0"}, tools)
        args = {"flag": True, "fields": ["a", "b"], "doc": {"k": 1}, "nothing": None}
        r = self.call(server, "t", args)
        self.assertIs(r["result"]["isError"], False)
        self.assertEqual(seen, args)
        bad = self.call(server, "t", {"flag": "yes"})
        self.assertIs(bad["result"]["isError"], True)
        self.assertIn("boolean", bad["result"]["content"][0]["text"])


class ReusablePlumbingTest(unittest.TestCase):
    def test_sibling_server_gets_its_own_identity(self):
        m = load_server_module()
        server = m.McpServer({"name": "sibling", "version": "9"}, {})
        r = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, None)
        self.assertEqual(r["result"]["serverInfo"], {"name": "sibling", "version": "9"})
        self.assertEqual(m.build_server().info["name"], SERVER_NAME)
        self.assertEqual(m.SERVER_INFO["name"], SERVER_NAME)


class ServerNameConsistencyTest(unittest.TestCase):
    """One server name everywhere: server, README, agent/command wiring, profiles."""

    def frontmatter_tools(self, path, key):
        text = (REPO / path).read_text(encoding="utf-8")
        line = re.search(rf"^{key}:\s*\[(.*)\]\s*$", text, re.M).group(1)
        return {t.strip() for t in line.split(",")}

    def test_readme_names_the_server(self):
        readme = (REPO / "infra/mcp-servers/scheduler-mcp/README.md").read_text(encoding="utf-8")
        self.assertIn(f"claude mcp add {SERVER_NAME}", readme)
        self.assertIn(f"mcp__{SERVER_NAME}__", readme)
        self.assertNotIn("claude mcp add scheduler ", readme)
        for stale in ("window_days", '["pct"]'):
            self.assertNotIn(stale, readme)

    def test_agent_and_command_allow_the_concrete_tools(self):
        prefix = f"mcp__{SERVER_NAME}__"
        planner = self.frontmatter_tools("core/agents/production-planner.md", "tools")
        status = self.frontmatter_tools("core/commands/order-status.md", "allowed-tools")
        self.assertLessEqual({"Read", "Grep", "Glob", "Bash"}, planner)  # existing tools kept
        self.assertLessEqual({"Read", "Grep", "Glob", "Bash"}, status)
        self.assertLessEqual({prefix + t for t in TOOL_NAMES}, planner)
        self.assertLessEqual({prefix + "list_work_orders", prefix + "get_work_order_status"}, status)
        for allowed in (planner, status):
            for t in allowed:
                if t.startswith("mcp__"):
                    self.assertTrue(t.startswith(prefix) and t[len(prefix):] in TOOL_NAMES, t)

    def test_no_other_server_name_spellings_in_core_and_profiles(self):
        stale = re.compile(r"mcp__scheduler__|claude mcp add scheduler\b|\"scheduler-mcp\"")
        for path in list((REPO / "core").rglob("*.md")) + list((REPO / "profiles").rglob("*")):
            if path.is_file() and path.suffix in (".md", ".json"):
                self.assertIsNone(stale.search(path.read_text(encoding="utf-8")), path)
        for profile in (REPO / "profiles").glob("*/profile.json"):
            rec = json.loads(profile.read_text(encoding="utf-8")).get("mcp", {}).get("recommended", [])
            self.assertNotIn("scheduler-mcp", rec, profile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
