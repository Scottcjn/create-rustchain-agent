# create-rustchain-agent

**60-second onboarding for a RustChain-participating agent.** One command
scaffolds a working agent: an Ed25519 RTC wallet, a runnable `agent.py`, MCP
node configuration for `rustchain-mcp`, and the path to claim the First-Light
bounty.

## Use
```
uvx create-rustchain-agent my-agent
cd my-agent && python agent.py
```

## Capabilities
- Generates an Ed25519 RTC wallet (0600, gitignored)
- Writes `.mcp.json` with the selected `RUSTCHAIN_NODE` for rustchain-mcp
- Emits an agent that reads `/health` and `/wallet/balance?miner_id=...`
- `--register` registers a Beacon identity; this is the only network write
- `--node` configures both the generated agent and rustchain-mcp

## Limitations
Scaffolding is local-only by default (no network writes unless `--register`).
The generated MCP config does not import `wallet.json`; rustchain-mcp wallet
tools use their own encrypted keystore. Requires `cryptography`.

Part of the RustChain ecosystem · pip: create-rustchain-agent · MIT.
