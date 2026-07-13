# SPDX-License-Identifier: MIT
import hashlib
import json
import os
import stat
import subprocess
import sys
import threading
import unittest
from contextlib import contextmanager, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from create_rustchain_agent import __main__ as cli
from create_rustchain_agent.templates import PROFILES


@contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextmanager
def local_node():
    NodeHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), NodeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def scaffold(name, node_url="https://node.example", profile="observer"):
    with redirect_stdout(StringIO()):
        return cli.scaffold(name, node_url, False, profile)


class NodeHandler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        self.requests.append((self.command, self.path))
        if self.path == "/health":
            self._json_response({"ok": True})
        elif self.path == "/epoch":
            self._json_response({"epoch": 42})
        elif self.path.startswith("/wallet/balance?miner_id=RTC"):
            self._json_response({"amount_rtc": 12.5})
        else:
            self.send_error(404)

    def do_POST(self):
        self.requests.append((self.command, self.path))
        self.send_error(405)

    def _json_response(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        pass


class ScaffoldTests(unittest.TestCase):
    def test_generated_wallet_matches_address_and_is_private(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            self.assertEqual(scaffold("test-agent"), 0)

            wallet_path = Path("test-agent/wallet.json")
            wallet = json.loads(wallet_path.read_text(encoding="utf-8"))
            expected = (
                "RTC"
                + hashlib.sha256(bytes.fromhex(wallet["public_key"])).hexdigest()[:40]
            )

            self.assertEqual(wallet["address"], expected)
            self.assertEqual(stat.S_IMODE(wallet_path.stat().st_mode), 0o600)
            self.assertIn("wallet.json", Path("test-agent/.gitignore").read_text())

    def test_every_profile_generates_expected_files_and_guidance(self):
        expected_files = {
            "observer": {
                "agent.py",
                "wallet.json",
                ".mcp.json",
                "README.md",
                ".gitignore",
            },
            "miner": {
                "agent.py",
                "wallet.json",
                ".mcp.json",
                "README.md",
                ".gitignore",
                "miner-config.json",
            },
            "bottube-creator": {
                "agent.py",
                "wallet.json",
                ".mcp.json",
                "README.md",
                ".gitignore",
                ".env.example",
                "draft.json",
            },
        }
        guidance = {
            "observer": "## 60-second start",
            "miner": "## Activate explicitly",
            "bottube-creator": "## Preview a draft",
        }

        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            for profile in PROFILES:
                with self.subTest(profile=profile):
                    target = f"agent-{profile}"
                    self.assertEqual(scaffold(target, profile=profile), 0)
                    generated = {path.name for path in Path(target).iterdir()}
                    self.assertEqual(generated, expected_files[profile])
                    agent_source = Path(target, "agent.py").read_text(encoding="utf-8")
                    compile(agent_source, str(Path(target, "agent.py")), "exec")
                    readme = Path(target, "README.md").read_text(encoding="utf-8")
                    self.assertIn(guidance[profile], readme)

    def test_mcp_config_uses_supported_node_setting_for_every_profile(self):
        node_url = "https://node.example/rustchain"
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            for profile in PROFILES:
                with self.subTest(profile=profile):
                    target = f"agent-{profile}"
                    scaffold(target, node_url, profile)

                    config = json.loads(
                        Path(target, ".mcp.json").read_text(encoding="utf-8")
                    )
                    server = config["mcpServers"]["rustchain"]
                    self.assertEqual(server["command"], "uvx")
                    self.assertEqual(server["args"], ["rustchain-mcp"])
                    self.assertEqual(server["env"], {"RUSTCHAIN_NODE": node_url})
                    self.assertNotIn("RUSTCHAIN_WALLET", server["env"])

                    readme = Path(target, "README.md").read_text(encoding="utf-8")
                    self.assertIn("separate encrypted keystore", readme)
                    self.assertNotIn("claude mcp add", readme)

    def test_observer_uses_only_live_read_contracts(self):
        with local_node() as node_url:
            with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
                scaffold("test-agent", node_url, "observer")
                result = subprocess.run(
                    [sys.executable, "agent.py"],
                    cwd="test-agent",
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                )

        self.assertIn("Node health: True", result.stdout)
        self.assertIn("Balance: 12.5 RTC", result.stdout)
        self.assertEqual(NodeHandler.requests[0], ("GET", "/health"))
        self.assertRegex(
            NodeHandler.requests[1][1],
            r"^/wallet/balance\?miner_id=RTC[0-9a-f]{40}$",
        )
        self.assertEqual({method for method, _path in NodeHandler.requests}, {"GET"})

    def test_miner_is_disabled_and_only_prints_activation_commands(self):
        with local_node() as node_url:
            with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
                scaffold("test-miner", node_url, "miner")
                config = json.loads(
                    Path("test-miner/miner-config.json").read_text(encoding="utf-8")
                )
                default_run = subprocess.run(
                    [sys.executable, "agent.py"],
                    cwd="test-miner",
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                )
                command_run = subprocess.run(
                    [sys.executable, "agent.py", "--show-activation-commands"],
                    cwd="test-miner",
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                )

        self.assertFalse(config["attestation_enabled"])
        self.assertFalse(config["auto_enroll"])
        self.assertEqual(
            config["activation_commands"], ["clawrtc install", "clawrtc start"]
        )
        self.assertIn("No enrollment or attestation was submitted", default_run.stdout)
        self.assertIn("clawrtc install", command_run.stdout)
        self.assertIn("clawrtc start", command_run.stdout)
        self.assertEqual({method for method, _path in NodeHandler.requests}, {"GET"})
        self.assertEqual(
            [path for _method, path in NodeHandler.requests],
            ["/health", "/epoch", "/health", "/epoch"],
        )

    def test_bottube_creator_enforces_local_dry_run_without_credentials(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            scaffold("test-creator", profile="bottube-creator")
            source = Path("test-creator/agent.py").read_text(encoding="utf-8")
            env_example = Path("test-creator/.env.example").read_text(encoding="utf-8")

            clean_env = os.environ.copy()
            for key in list(clean_env):
                if key.startswith("BOTTUBE_"):
                    clean_env.pop(key)
            clean_env["BOTTUBE_API_KEY"] = "test-secret-must-not-print"
            preview = subprocess.run(
                [sys.executable, "agent.py"],
                cwd="test-creator",
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            unsafe_env = clean_env.copy()
            unsafe_env["BOTTUBE_DRY_RUN"] = "false"
            refused = subprocess.run(
                [sys.executable, "agent.py"],
                cwd="test-creator",
                env=unsafe_env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("POST", source)
        self.assertIn("BOTTUBE_API_KEY=replace-with-your-agent-api-key", env_example)
        self.assertIn("BOTTUBE_DRY_RUN=true", env_example)
        self.assertIn("No upload or post was attempted", preview.stdout)
        self.assertNotIn("test-secret-must-not-print", preview.stdout)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("requires BOTTUBE_DRY_RUN=true", refused.stdout)

    def test_generated_templates_do_not_embed_service_credentials(self):
        forbidden_markers = (
            "moltbook_sk_",
            "clawchan_",
            "rustchain_admin_key_",
        )
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            for profile in PROFILES:
                target = f"agent-{profile}"
                scaffold(target, profile=profile)
                for path in Path(target).iterdir():
                    if path.name == "wallet.json":
                        continue
                    content = path.read_text(encoding="utf-8")
                    for marker in forbidden_markers:
                        self.assertNotIn(marker, content)
                    self.assertNotRegex(
                        content,
                        r"(?i)\b(?:password|passwd)\s*[:=]\s*[^\s]{8,}",
                    )

    def test_cli_help_lists_profiles_and_network_write_boundary(self):
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            cli.main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = output.getvalue()
        self.assertIn("--profile {observer,miner,bottube-creator}", help_text)
        self.assertIn("default: observer", help_text)
        self.assertIn("network write", help_text)

    def test_default_cli_invocation_remains_observer_compatible(self):
        with mock.patch.object(cli, "scaffold", return_value=0) as scaffold_call:
            self.assertEqual(cli.main(["my-agent"]), 0)

        scaffold_call.assert_called_once_with("my-agent", cli.NODE_URL, False)

    def test_cli_dispatches_explicit_profiles(self):
        for profile in ("miner", "bottube-creator"):
            with self.subTest(profile=profile):
                with mock.patch.object(
                    cli, "scaffold", return_value=0
                ) as scaffold_call:
                    self.assertEqual(
                        cli.main(["my-agent", "--profile", profile]),
                        0,
                    )
                scaffold_call.assert_called_once_with(
                    "my-agent", cli.NODE_URL, False, profile
                )

    def test_existing_directory_is_not_modified(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            target = Path("test-agent")
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("mine", encoding="utf-8")

            self.assertEqual(scaffold("test-agent"), 1)
            self.assertEqual(marker.read_text(encoding="utf-8"), "mine")

    def test_invalid_profile_does_not_create_directory(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            with redirect_stdout(StringIO()):
                result = cli.scaffold(
                    "test-agent", "https://node.example", False, "publisher"
                )
            self.assertEqual(result, 2)
            self.assertFalse(Path("test-agent").exists())

    def test_registration_is_opt_in(self):
        with TemporaryDirectory() as tmpdir, working_directory(tmpdir):
            with mock.patch.object(cli, "_register_beacon") as register:
                scaffold("local-agent")
                register.assert_not_called()

                with redirect_stdout(StringIO()):
                    cli.scaffold(
                        "registered-agent", "https://node.example", True, "observer"
                    )
                register.assert_called_once()

    def test_project_docs_cover_all_profiles_and_security_boundaries(self):
        readme = (
            Path(__file__).parents[1].joinpath("README.md").read_text(encoding="utf-8")
        )
        for profile in PROFILES:
            self.assertIn(profile, readme)
        self.assertIn("RUSTCHAIN_NODE", readme)
        self.assertIn("explicit user action", readme)
        self.assertIn("no HTTP client or posting", readme)
        self.assertIn("--register", readme)


if __name__ == "__main__":
    unittest.main()
