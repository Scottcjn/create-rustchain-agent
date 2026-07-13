# create-rustchain-agent

Scaffold a safe-by-default RustChain agent with profile-specific files, an
Ed25519 RTC wallet, and `rustchain-mcp` wiring.

## Use

```bash
uvx create-rustchain-agent my-agent
uvx create-rustchain-agent my-miner --profile miner
uvx create-rustchain-agent my-creator --profile bottube-creator
```

## Profiles

- `observer` (default): read-only node health and wallet balance inspection;
  this preserves the original no-flag behavior.
- `miner`: disabled miner configuration plus activation commands that are only
  printed for review after an explicit flag; it never auto-enrolls or attests.
- `bottube-creator`: placeholder environment and draft files with an enforced
  local dry run; it contains no posting implementation or embedded credential.

## Capabilities

- Generates an Ed25519 RTC wallet (`0600`, gitignored).
- Writes `.mcp.json` with the selected `RUSTCHAIN_NODE` for `rustchain-mcp`.
- Writes profile-specific `agent.py` and README guidance.
- Supports `--node` for both the generated agent and MCP server.
- Supports explicit `--register` Beacon registration as the only generator
  network write.

## Boundaries

Scaffolding is local-only unless the user explicitly passes `--register`. The
MCP config does not import `wallet.json`; MCP wallet tools use their own encrypted
keystore. The BoTTube profile accepts agent placeholders only and must never be
configured with human account credentials. Requires `cryptography`.

Part of the RustChain ecosystem; package: `create-rustchain-agent`; MIT.
