# SPDX-License-Identifier: MIT
"""`uvx create-rustchain-agent <name>` — scaffold a RustChain agent in ~60s.

Local-only by default. Generates:
  <name>/
    wallet.json        Ed25519 RTC wallet (gitignored; PRIVATE KEY inside)
    agent.py           runnable: checks balance, claims the First-Light bounty
    .mcp.json          rustchain-mcp wired to the selected RustChain node
    .gitignore         excludes wallet.json
    README.md          next steps + editor MCP setup

Pass --register to also register a Beacon identity on the network (a write).
"""

import argparse
import hashlib
import json
import os
import sys
import time

NODE_URL = "https://rustchain.org"

C = {"g": "\033[32m", "y": "\033[33m", "c": "\033[36m", "d": "\033[2m",
     "b": "\033[1m", "r": "\033[31m", "x": "\033[0m"}


def _gen_wallet():
    """Generate an Ed25519 RTC wallet (address = RTC + sha256(pubkey)[:40])."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat)
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


AGENT_PY = '''#!/usr/bin/env python3
"""{name} — a RustChain-participating agent (scaffolded by create-rustchain-agent).

First run: checks the node is reachable, prints your RTC address + balance, and
shows how to claim the First-Light newcomer bounty so your wallet is funded.
"""
import json
import os
import urllib.parse
import urllib.request

NODE_URL = "{node}"
WALLET = os.path.join(os.path.dirname(__file__), "wallet.json")


def _get(path):
    with urllib.request.urlopen(NODE_URL.rstrip("/") + path, timeout=15) as r:
        return json.loads(r.read().decode())


def main():
    with open(WALLET, encoding="utf-8") as wallet_file:
        w = json.load(wallet_file)
    print(f"Agent wallet: {{w['address']}}")
    try:
        print("Node health:", _get("/health").get("ok", "?"))
    except Exception as e:
        print("Node unreachable:", e); return
    try:
        query = urllib.parse.urlencode({{"miner_id": w["address"]}})
        balance = _get("/wallet/balance?" + query)
        amount = balance.get("amount_rtc", balance.get("balance_rtc"))
        print("Balance:", f"{{amount}} RTC" if amount is not None else balance)
    except Exception as e:
        print("Balance lookup failed (new wallet is fine):", e)
    print()
    print("Claim your First-Light newcomer bounty to fund this wallet:")
    print("  1. open a [First-Light] claim issue on the rustchain-bounties repo")
    print(f"  2. paste your address: {{w['address']}}")
    print("  3. once paid, spend it:  clawrtc tip <peer> 0.5   (clawrtc spend SDK)")


if __name__ == "__main__":
    main()
'''

README_MD = '''# {name}

A RustChain-participating agent, scaffolded by `create-rustchain-agent`.

## What you got
- `wallet.json` — your Ed25519 RTC wallet (**private key inside; gitignored**)
- `agent.py` — run `python agent.py` to check the node + your balance
- `.mcp.json` — `rustchain-mcp` pointed at the same RustChain node

## Your RTC address
```
{address}
```

## 60-second start
1. `python agent.py` — confirms the node is reachable and shows your balance.
2. **Fund it** — claim the First-Light newcomer bounty (open a `[First-Light]`
   claim issue on `Scottcjn/rustchain-bounties`, paste the address above).
3. **Spend it** — install the spend SDK and use your RTC:
   ```
   pip install clawrtc
   clawrtc tip <peer-address> 0.5      # tip a peer
   clawrtc gas 1.0                     # top up gas
   clawrtc pay <address> 2.0 --dry-run # preview a transfer (safe)
   ```

## Wire the MCP into your editor
- **Claude Code:** open this project and review/approve its `.mcp.json` server.
- **Cursor / Cline:** copy the `rustchain` entry from `.mcp.json` into the
  editor's project MCP configuration if it is not discovered automatically.

`.mcp.json` points `rustchain-mcp` at the same node as `agent.py`. It does not
import `wallet.json`; the MCP wallet tools keep a separate encrypted keystore.
Keep `wallet.json` private.

## Mine (optional — earn RTC on real hardware)
```
clawrtc install && clawrtc start    # vintage/exotic HW earns bonus multipliers
```
'''

GITIGNORE = "wallet.json\n__pycache__/\n*.pyc\n.env\n"


def scaffold(name, node_url, do_register):
    if os.path.exists(name):
        print(f"{C['r']}Directory '{name}' already exists — aborting.{C['x']}")
        return 1
    os.makedirs(name)
    wallet = _gen_wallet()
    with open(os.path.join(name, "wallet.json"), "w", encoding="utf-8") as f:
        json.dump(wallet, f, indent=2)
    os.chmod(os.path.join(name, "wallet.json"), 0o600)
    with open(os.path.join(name, "agent.py"), "w", encoding="utf-8") as f:
        f.write(AGENT_PY.format(name=name, node=node_url))
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
    with open(os.path.join(name, "README.md"), "w", encoding="utf-8") as f:
        f.write(README_MD.format(name=name, address=wallet["address"]))
    with open(os.path.join(name, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(GITIGNORE)

    print(f"\n{C['g']}{C['b']}✓ Scaffolded '{name}'{C['x']}")
    print(f"  {C['d']}RTC address:{C['x']} {C['b']}{wallet['address']}{C['x']}")
    print(f"  {C['d']}wallet.json is 0600 + gitignored — back it up; the key can't be recovered.{C['x']}")

    if do_register:
        _register_beacon(wallet, node_url)

    print(f"\n{C['c']}Next:{C['x']}")
    print(f"  cd {name} && python agent.py")
    print(f"  Open {name}/ in your MCP-compatible editor; .mcp.json is ready")
    print(f"  {C['d']}Fund via First-Light bounty, then: pip install clawrtc && clawrtc tip ...{C['x']}\n")
    return 0


def _register_beacon(wallet, node_url):
    """Optional network write: register a Beacon identity for this wallet."""
    import urllib.request
    print(f"\n{C['y']}--register: registering Beacon identity (network write)...{C['x']}")
    pub_bytes = bytes.fromhex(wallet["public_key"])
    agent_id = "bcn_" + hashlib.sha256(pub_bytes).hexdigest()[:12]
    payload = json.dumps({
        "agent_id": agent_id,
        "pubkey_hex": wallet["public_key"],
    }).encode()
    try:
        req = urllib.request.Request(
            node_url.rstrip("/") + "/beacon/join",
            data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"  {C['g']}Beacon:{C['x']}", json.loads(r.read().decode()))
    except Exception as e:
        print(f"  {C['y']}Beacon registration skipped/failed ({e}).{C['x']}")
        print(f"  {C['d']}Register later: beacon atlas register{C['x']}")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="create-rustchain-agent",
        description="Scaffold a RustChain-participating agent in ~60 seconds.")
    p.add_argument("name", help="project/agent directory name to create")
    p.add_argument("--node", default=NODE_URL, help=f"node URL (default {NODE_URL})")
    p.add_argument("--register", action="store_true",
                   help="also register a Beacon identity (a network write)")
    args = p.parse_args(argv)
    try:
        import cryptography  # noqa: F401
    except ImportError:
        print(f"{C['r']}Needs 'cryptography'. Run: pip install cryptography{C['x']}")
        return 1
    return scaffold(args.name, args.node, args.register)


if __name__ == "__main__":
    sys.exit(main())
