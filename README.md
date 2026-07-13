# create-rustchain-agent

**60-second onboarding for a RustChain-participating agent.** One command
scaffolds a working agent: an Ed25519 RTC wallet, a runnable `agent.py`, MCP
node configuration for `rustchain-mcp`, and the path to claim the First-Light
newcomer bounty.

```bash
uvx create-rustchain-agent my-agent
# or: pipx run create-rustchain-agent my-agent
cd my-agent && python agent.py
```

## What it generates
| File | Purpose |
|------|---------|
| `wallet.json` | Ed25519 RTC wallet (**private key inside; 0600 + gitignored**) |
| `agent.py` | checks `/health` and `/wallet/balance?miner_id=...`; shows how to claim First-Light |
| `.mcp.json` | runs `rustchain-mcp` against the selected `RUSTCHAIN_NODE` |
| `README.md` | next steps + editor MCP setup |
| `.gitignore` | excludes `wallet.json` |

## Safe by default
Scaffolding is **local only**: it generates files and a wallet, with no network
writes. The generated `agent.py` performs read-only health and balance requests.
Pass `--register` to also register a Beacon identity; that flag performs a
network write. Use `--node <url>` to point both `agent.py` and `rustchain-mcp`
at a testnet or alternate node.

The generated `.mcp.json` configures the MCP server's node URL. It does not
import `wallet.json`; `rustchain-mcp` maintains its own encrypted keystore for
wallet tools. Review and approve the project-scoped MCP server when your editor
prompts. Keep `wallet.json` private even though it is gitignored and mode `0600`.

## Options

```text
--node URL   RustChain node used by agent.py and .mcp.json
--register   Register a Beacon identity after scaffolding (network write)
```

## The arc it sets up
1. **Scaffold** → you have a funded-capable wallet + a participating agent.
2. **Fund** → claim the First-Light newcomer bounty (paste your address).
3. **Spend** → `pip install clawrtc` and use `clawrtc tip/gas/pay` (the spend SDK).
4. **Mine** (optional) → `clawrtc install && clawrtc start` — real/vintage
   hardware earns Proof-of-Antiquity bonus multipliers.

Part of the [RustChain](https://rustchain.org) ecosystem.

## Development

The test suite is offline: it runs generated agents against a local HTTP server
and never registers identities or submits transactions.

```bash
python -m unittest discover -s tests -v
```

## License
MIT © Elyan Labs.
