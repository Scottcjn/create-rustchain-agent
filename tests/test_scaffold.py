# SPDX-License-Identifier: MIT
import hashlib
import json
import os
import stat
import subprocess
import sys
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from create_rustchain_agent import __main__ as cli


@contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class NodeHandler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        self.requests.append(self.path)
        if self.path == "/health":
            self._json_response({"ok": True})
        elif self.path.startswith("/wallet/balance?miner_id=RTC"):
            self._json_response({"amount_rtc": 12.5})
        else:
            self.send_error(404)

    def _json_response(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        pass


class BeaconNodeHandler(BaseHTTPRequestHandler):
    """Mirrors the real node contract: registration is POST /beacon/join,
    requiring agent_id + pubkey_hex, and a canonical bcn_<hash> agent_id must
    equal bcn_ + sha256(pubkey_bytes)[:12]. Any other path 404s (nginx)."""

    requests = []
    registered = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        self.requests.append(self.path)
        if self.path != "/beacon/join":
            self.send_error(404)
            return
        agent_id = body.get("agent_id")
        pubkey_hex = body.get("pubkey_hex")
        if not agent_id or not pubkey_hex:
            self.send_error(400, "Missing required field")
            return
        expected = "bcn_" + hashlib.sha256(bytes.fromhex(pubkey_hex)).hexdigest()[:12]
        if agent_id != expected:
            self.send_error(400, "canonical bcn_<hash> must match pubkey_hex")
            return
        self.registered.append(agent_id)
        body_out = json.dumps({"ok": True, "agent_id": agent_id, "status": "active"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_out)))
        self.end_headers()
        self.wfile.write(body_out)

    def log_message(self, _format, *_args):
        pass


class RegisterBeaconTests(unittest.TestCase):
    def test_register_hits_beacon_join_with_canonical_agent_id(self):
        BeaconNodeHandler.requests = []
        BeaconNodeHandler.registered = []
        wallet = cli._gen_wallet()
        server = ThreadingHTTPServer(("127.0.0.1", 0), BeaconNodeHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            node_url = f"http://127.0.0.1:{server.server_address[1]}"
            cli._register_beacon(wallet, node_url)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        # Registration must reach /beacon/join (not the old atlas/register path)
        # and succeed, meaning the derived canonical agent_id matched the pubkey.
        self.assertEqual(BeaconNodeHandler.requests, ["/beacon/join"])
        expected = "bcn_" + hashlib.sha256(
            bytes.fromhex(wallet["public_key"])
        ).hexdigest()[:12]
        self.assertEqual(BeaconNodeHandler.registered, [expected])


class ScaffoldTests(unittest.TestCase):
    def test_generated_wallet_matches_address_and_is_private(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            self.assertEqual(cli.scaffold("test-agent", "https://node.example", False), 0)

            wallet_path = Path("test-agent/wallet.json")
            wallet = json.loads(wallet_path.read_text(encoding="utf-8"))
            expected = "RTC" + hashlib.sha256(
                bytes.fromhex(wallet["public_key"])
            ).hexdigest()[:40]

            self.assertEqual(wallet["address"], expected)
            self.assertEqual(stat.S_IMODE(wallet_path.stat().st_mode), 0o600)
            self.assertIn("wallet.json", Path("test-agent/.gitignore").read_text())

    def test_mcp_config_uses_supported_node_setting(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            cli.scaffold("test-agent", "https://node.example/rustchain", False)

            config = json.loads(Path("test-agent/.mcp.json").read_text(encoding="utf-8"))
            server = config["mcpServers"]["rustchain"]
            self.assertEqual(server["env"], {"RUSTCHAIN_NODE": "https://node.example/rustchain"})
            self.assertNotIn("RUSTCHAIN_WALLET", server["env"])

            readme = Path("test-agent/README.md").read_text(encoding="utf-8")
            self.assertIn("separate encrypted keystore", readme)
            self.assertNotIn("claude mcp add", readme)

    def test_generated_agent_uses_live_balance_contract(self):
        NodeHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), NodeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        node_url = f"http://127.0.0.1:{server.server_port}"

        try:
            with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
                cli.scaffold("test-agent", node_url, False)
                result = subprocess.run(
                    [sys.executable, "agent.py"],
                    cwd="test-agent",
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertIn("Node health: True", result.stdout)
        self.assertIn("Balance: 12.5 RTC", result.stdout)
        self.assertEqual(NodeHandler.requests[0], "/health")
        self.assertRegex(NodeHandler.requests[1], r"^/wallet/balance\?miner_id=RTC[0-9a-f]{40}$")

    def test_existing_directory_is_not_modified(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            target = Path("test-agent")
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("mine", encoding="utf-8")

            self.assertEqual(cli.scaffold("test-agent", "https://node.example", False), 1)
            self.assertEqual(marker.read_text(encoding="utf-8"), "mine")

    def test_registration_is_opt_in(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            with mock.patch.object(cli, "_register_beacon") as register:
                cli.scaffold("local-agent", "https://node.example", False)
                register.assert_not_called()

                cli.scaffold("registered-agent", "https://node.example", True)
                register.assert_called_once()


if __name__ == "__main__":
    unittest.main()
