# SPDX-License-Identifier: MIT
"""Generated file templates for each RustChain agent profile."""

import json


PROFILES = ("observer", "miner", "bottube-creator")

GITIGNORE = "wallet.json\n__pycache__/\n*.pyc\n.env\n"


OBSERVER_AGENT_PY = '''#!/usr/bin/env python3
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


MINER_AGENT_PY = '''#!/usr/bin/env python3
"""{name} - a safe-by-default RustChain miner scaffold.

The default command performs read-only node inspection. It never enrolls or
submits an attestation. Use --show-activation-commands to review the separate
commands that a user may explicitly run when ready.
"""
import argparse
import json
import os
import urllib.request

NODE_URL = "{node}"
ROOT = os.path.dirname(__file__)
WALLET = os.path.join(ROOT, "wallet.json")
CONFIG = os.path.join(ROOT, "miner-config.json")


def _get(path):
    with urllib.request.urlopen(NODE_URL.rstrip("/") + path, timeout=15) as r:
        return json.loads(r.read().decode())


def _load(path):
    with open(path, encoding="utf-8") as source:
        return json.load(source)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Inspect a RustChain node for miner readiness."
    )
    parser.add_argument(
        "--show-activation-commands",
        action="store_true",
        help="print, but do not run, the commands that activate mining",
    )
    args = parser.parse_args(argv)
    wallet = _load(WALLET)
    config = _load(CONFIG)

    print(f"Miner wallet: {{wallet['address']}}")
    print("Attestation enabled:", config["attestation_enabled"])
    print("Automatic enrollment:", config["auto_enroll"])
    try:
        print("Node health:", _get("/health").get("ok", "?"))
        epoch = _get("/epoch")
        print("Current epoch:", epoch.get("epoch", epoch.get("current_epoch", "?")))
    except Exception as error:
        print("Node inspection failed:", error)
        return 1

    if args.show_activation_commands:
        print("\\nReview, then run these commands yourself to activate mining:")
        for command in config["activation_commands"]:
            print("  " + command)
    else:
        print("\\nRead-only inspection complete. No enrollment or attestation was submitted.")
        print("Run 'python agent.py --show-activation-commands' to review next steps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


BOTTUBE_CREATOR_AGENT_PY = '''#!/usr/bin/env python3
"""{name} - prepare and preview a BoTTube creator draft locally.

This generated program deliberately contains no posting implementation. It
reads a local draft and placeholder environment configuration, then prints a
dry-run preview without making a network request.
"""
import argparse
import json
import os

ROOT = os.path.dirname(__file__)
DEFAULT_DRAFT = os.path.join(ROOT, "draft.json")


def _is_true(value):
    return value.strip().lower() in {{"1", "true", "yes", "on"}}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Preview a BoTTube creator draft locally."
    )
    parser.add_argument("--draft", default=DEFAULT_DRAFT, help="draft JSON file to preview")
    args = parser.parse_args(argv)

    with open(args.draft, encoding="utf-8") as source:
        draft = json.load(source)

    api_url = os.environ.get("BOTTUBE_API_URL", "https://bottube.ai")
    agent_slug = os.environ.get("BOTTUBE_AGENT_SLUG", "replace-with-your-agent-slug")
    dry_run = _is_true(os.environ.get("BOTTUBE_DRY_RUN", "true"))
    if not dry_run:
        print("Refusing to continue: this scaffold requires BOTTUBE_DRY_RUN=true.")
        return 2

    print("BoTTube creator dry run")
    print("API URL:", api_url)
    print("Agent slug:", agent_slug)
    print("API key configured:", bool(os.environ.get("BOTTUBE_API_KEY")))
    print(json.dumps(draft, indent=2))
    print("No upload or post was attempted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


OBSERVER_README_MD = """# {name}

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
"""


MINER_README_MD = """# {name}

A safe-by-default RustChain miner scaffold generated with the `miner` profile.

## What you got
- `wallet.json` - your Ed25519 RTC wallet (**private key inside; gitignored**)
- `agent.py` - read-only node health and epoch inspection
- `miner-config.json` - mining disabled, with activation commands for review
- `.mcp.json` - `rustchain-mcp` configured with `RUSTCHAIN_NODE={node}`

## Your RTC address
```
{address}
```

## Inspect safely
```bash
python agent.py
```

That command only sends `GET` requests to `/health` and `/epoch`. The generated
configuration sets `attestation_enabled` and `auto_enroll` to `false`. The
scaffold never runs a miner, enrolls hardware, or submits attestations for you.

## Activate explicitly
```bash
python agent.py --show-activation-commands
```

This prints the commands in `miner-config.json`; it still does not execute them.
Review your node, wallet, hardware identity, and the current RustChain mining
documentation before manually running either command.

## Wire the MCP into your editor
Open this project and review/approve `.mcp.json`. It passes the selected node as
the supported `RUSTCHAIN_NODE` environment variable. It does not import
`wallet.json`; MCP wallet tools use a separate encrypted keystore.
"""


BOTTUBE_CREATOR_README_MD = """# {name}

A local-first BoTTube creator scaffold generated with the `bottube-creator`
profile. It previews draft metadata and never uploads or posts automatically.

## What you got
- `wallet.json` - your Ed25519 RTC wallet (**private key inside; gitignored**)
- `agent.py` - a local, enforced dry-run draft preview
- `draft.json` - placeholder metadata for one video draft
- `.env.example` - placeholder BoTTube agent configuration, with dry-run
  enabled
- `.mcp.json` - `rustchain-mcp` configured with `RUSTCHAIN_NODE={node}`

## Your RTC address
```
{address}
```

## Preview a draft
1. Edit `draft.json` with local video metadata.
2. Optionally copy `.env.example` to `.env` and replace placeholders for your
   own agent identity. `.env` is gitignored; `agent.py` does not load it for you.
3. Export the variables in your shell, then run:

   ```bash
   python agent.py
   ```

The generated program has no HTTP client or posting implementation. It refuses
to continue when `BOTTUBE_DRY_RUN` is false and never prints the API key. Connect
a separately reviewed, documented agent upload flow only when you intentionally
choose to publish. Never use a human account credential in this project.

## Wire the MCP into your editor
Open this project and review/approve `.mcp.json`. It passes the selected node as
the supported `RUSTCHAIN_NODE` environment variable. It does not import either
`wallet.json` or BoTTube credentials.
MCP wallet tools use a separate encrypted keystore.
"""


BOTTUBE_ENV_EXAMPLE = """# Placeholder agent credentials only. Never use a human account here.
BOTTUBE_API_URL=https://bottube.ai
BOTTUBE_API_KEY=replace-with-your-agent-api-key
BOTTUBE_AGENT_SLUG=replace-with-your-agent-slug
BOTTUBE_DRY_RUN=true
"""


def _miner_config(address):
    return {
        "profile": "miner",
        "wallet_address": address,
        "attestation_enabled": False,
        "auto_enroll": False,
        "activation_commands": ["clawrtc install", "clawrtc start"],
    }


def _bottube_draft():
    return {
        "title": "replace-with-video-title",
        "description": "replace-with-video-description",
        "video_path": "replace-with-local-video-path",
        "tags": [],
    }


def render_profile_files(profile, name, node_url, address):
    """Return profile-specific generated files keyed by relative path."""
    values = {"name": name, "node": node_url, "address": address}
    if profile == "observer":
        return {
            "agent.py": OBSERVER_AGENT_PY.format(**values),
            "README.md": OBSERVER_README_MD.format(**values),
        }
    if profile == "miner":
        return {
            "agent.py": MINER_AGENT_PY.format(**values),
            "miner-config.json": json.dumps(_miner_config(address), indent=2) + "\n",
            "README.md": MINER_README_MD.format(**values),
        }
    if profile == "bottube-creator":
        return {
            "agent.py": BOTTUBE_CREATOR_AGENT_PY.format(**values),
            "draft.json": json.dumps(_bottube_draft(), indent=2) + "\n",
            ".env.example": BOTTUBE_ENV_EXAMPLE,
            "README.md": BOTTUBE_CREATOR_README_MD.format(**values),
        }
    raise ValueError("unknown profile: " + profile)


def next_steps(profile):
    """Return concise terminal guidance for a completed scaffold."""
    if profile == "miner":
        return (
            "python agent.py",
            "python agent.py --show-activation-commands",
        )
    if profile == "bottube-creator":
        return (
            "edit draft.json and review .env.example",
            "python agent.py  # enforced dry run",
        )
    return (
        "python agent.py",
        "Fund via First-Light bounty, then: pip install clawrtc && clawrtc tip ...",
    )
