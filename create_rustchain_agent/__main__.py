# SPDX-License-Identifier: MIT
"""`uvx create-rustchain-agent <name>` — scaffold a RustChain agent in ~60s.

Local-only by default. Generates:
  <name>/
    wallet.json        Ed25519 RTC wallet (gitignored; PRIVATE KEY inside)
    agent.py           runnable behavior selected by --profile
    .mcp.json          rustchain-mcp wired to the selected RustChain node
    .gitignore         excludes wallet.json
    README.md          profile-specific next steps + editor MCP setup

Pass --register to also register a Beacon identity on the network (a write).
"""

import argparse
import hashlib
import ipaddress
import json
import os
import re
import sys
import time
from urllib.parse import urlsplit, urlunsplit

from .templates import GITIGNORE, PROFILES, next_steps, render_profile_files

NODE_URL = "https://rustchain.org"

C = {
    "g": "\033[32m",
    "y": "\033[33m",
    "c": "\033[36m",
    "d": "\033[2m",
    "b": "\033[1m",
    "r": "\033[31m",
    "x": "\033[0m",
}

_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_PATH_CHARACTERS = frozenset("/-._~!$&'()*+,;=:@")
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def _normalize_node_url(node_url):
    """Validate and normalize a node URL before generated files are created."""
    if not isinstance(node_url, str) or not node_url:
        raise ValueError("must be a non-empty string")
    if not node_url.isascii():
        raise ValueError("must contain ASCII characters only")
    if any(
        character.isspace() or ord(character) < 0x20 or ord(character) == 0x7F
        for character in node_url
    ):
        raise ValueError("must not contain whitespace or control characters")
    if "?" in node_url or "#" in node_url:
        raise ValueError("must not contain a query or fragment")

    try:
        parsed = urlsplit(node_url)
    except ValueError as error:
        raise ValueError("is malformed") from error
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("scheme must be http or https")
    if not parsed.netloc or parsed.hostname is None:
        raise ValueError("must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("must not include userinfo credentials")
    if parsed.netloc.endswith(":"):
        raise ValueError("contains an invalid port")

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("contains an invalid port") from error
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("contains an invalid port")

    hostname = parsed.hostname
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        hostname_without_dot = hostname[:-1] if hostname.endswith(".") else hostname
        labels = hostname_without_dot.split(".")
        if (
            not hostname_without_dot
            or len(hostname) > 253
            or any(not _HOST_LABEL.fullmatch(label) for label in labels)
        ):
            raise ValueError("contains an invalid host") from None
        normalized_host = hostname.lower()
    else:
        normalized_host = address.compressed
        if address.version == 6:
            normalized_host = f"[{normalized_host}]"

    path = parsed.path
    index = 0
    while index < len(path):
        character = path[index]
        if character.isalnum() or character in _PATH_CHARACTERS:
            index += 1
            continue
        if (
            character == "%"
            and index + 2 < len(path)
            and path[index + 1] in _HEX_DIGITS
            and path[index + 2] in _HEX_DIGITS
        ):
            decoded = int(path[index + 1 : index + 3], 16)
            if decoded < 0x20 or decoded == 0x7F:
                raise ValueError("path contains an encoded control character")
            index += 3
            continue
        raise ValueError("path contains an unsafe character")

    netloc = normalized_host
    if port is not None:
        netloc += f":{port}"
    normalized_path = path.rstrip("/")
    return urlunsplit((scheme, netloc, normalized_path, "", ""))


def _gen_wallet():
    """Generate an Ed25519 RTC wallet (address = RTC + sha256(pubkey)[:40])."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    privb = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    addr = "RTC" + hashlib.sha256(pub).hexdigest()[:40]
    return {
        "address": addr,
        "public_key": pub.hex(),
        "private_key": privb.hex(),
        "curve": "Ed25519",
        "network": "rustchain-mainnet",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def scaffold(name, node_url, do_register, profile="observer"):
    try:
        node_url = _normalize_node_url(node_url)
    except ValueError as error:
        print(f"{C['r']}Invalid node URL: {error}.{C['x']}")
        return 2
    if profile not in PROFILES:
        choices = ", ".join(PROFILES)
        print(f"{C['r']}Unknown profile '{profile}'. Choose from: {choices}.{C['x']}")
        return 2
    if os.path.exists(name):
        print(f"{C['r']}Directory '{name}' already exists — aborting.{C['x']}")
        return 1
    os.makedirs(name)
    wallet = _gen_wallet()
    with open(os.path.join(name, "wallet.json"), "w", encoding="utf-8") as f:
        json.dump(wallet, f, indent=2)
    os.chmod(os.path.join(name, "wallet.json"), 0o600)
    for relative_path, content in render_profile_files(
        profile, name, node_url, wallet["address"]
    ).items():
        with open(os.path.join(name, relative_path), "w", encoding="utf-8") as f:
            f.write(content)
    mcp_config = {
        "mcpServers": {
            "rustchain": {
                "command": "uvx",
                "args": ["rustchain-mcp"],
                "env": {"RUSTCHAIN_NODE": node_url},
            }
        }
    }
    with open(os.path.join(name, ".mcp.json"), "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)
        f.write("\n")
    with open(os.path.join(name, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(GITIGNORE)

    if profile == "observer":
        print(f"\n{C['g']}{C['b']}✓ Scaffolded '{name}'{C['x']}")
    else:
        print(f"\n{C['g']}{C['b']}✓ Scaffolded '{name}' ({profile}){C['x']}")
    print(f"  {C['d']}RTC address:{C['x']} {C['b']}{wallet['address']}{C['x']}")
    print(
        f"  {C['d']}wallet.json is 0600 + gitignored — back it up; the key can't be recovered.{C['x']}"
    )

    if do_register:
        _register_beacon(wallet, node_url)

    print(f"\n{C['c']}Next:{C['x']}")
    if profile == "observer":
        print(f"  cd {name} && python agent.py")
        print(f"  Open {name}/ in your MCP-compatible editor; .mcp.json is ready")
        print(
            f"  {C['d']}Fund via First-Light bounty, then: pip install clawrtc && clawrtc tip ...{C['x']}\n"
        )
    else:
        first, second = next_steps(profile)
        print(f"  cd {name} && {first}")
        print(f"  {second}")
        print(f"  Open {name}/ in your MCP-compatible editor; .mcp.json is ready\n")
    return 0


def _register_beacon(wallet, node_url):
    """Optional network write: register a Beacon identity for this wallet."""
    import urllib.request

    print(
        f"\n{C['y']}--register: registering Beacon identity (network write)...{C['x']}"
    )
    payload = json.dumps(
        {
            "pubkey_hex": wallet["public_key"],
            "rtc_address": wallet["address"],
        }
    ).encode()
    try:
        req = urllib.request.Request(
            node_url.rstrip("/") + "/beacon/atlas/register",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"  {C['g']}Beacon:{C['x']}", json.loads(r.read().decode()))
    except Exception as e:
        print(f"  {C['y']}Beacon registration skipped/failed ({e}).{C['x']}")
        print(f"  {C['d']}Register later: beacon atlas register{C['x']}")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="create-rustchain-agent",
        description="Scaffold a RustChain-participating agent in ~60 seconds.",
    )
    p.add_argument("name", help="project/agent directory name to create")
    p.add_argument("--node", default=NODE_URL, help=f"node URL (default {NODE_URL})")
    p.add_argument(
        "--profile",
        choices=PROFILES,
        default="observer",
        help="generated agent profile (default: observer)",
    )
    p.add_argument(
        "--register",
        action="store_true",
        help="also register a Beacon identity (a network write)",
    )
    args = p.parse_args(argv)
    try:
        import cryptography  # noqa: F401
    except ImportError:
        print(f"{C['r']}Needs 'cryptography'. Run: pip install cryptography{C['x']}")
        return 1
    if args.profile == "observer":
        return scaffold(args.name, args.node, args.register)
    return scaffold(args.name, args.node, args.register, args.profile)


if __name__ == "__main__":
    sys.exit(main())
