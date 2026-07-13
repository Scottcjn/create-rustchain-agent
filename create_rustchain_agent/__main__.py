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
import json
import os
import sys
import time

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
