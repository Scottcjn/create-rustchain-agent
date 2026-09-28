# create-rustchain-agent

**Safe, profile-based onboarding for a RustChain-participating agent.** One
command scaffolds an Ed25519 RTC wallet, a runnable `agent.py`, project-scoped
`rustchain-mcp` configuration, and guidance tailored to the selected profile.

```bash
uvx create-rustchain-agent my-agent
# Equivalent to: uvx create-rustchain-agent my-agent --profile observer
cd my-agent && python agent.py
```

Omitting `--profile` retains the original observer behavior.

## Profiles

### `observer` (default)

Creates the original read-only agent. Running `agent.py` sends `GET` requests
to `/health` and `/wallet/balance?miner_id=...`, then shows the First-Light
funding guidance. It does not submit transactions, enroll, attest, or post.

```bash
uvx create-rustchain-agent my-observer --profile observer
```

### `miner`

Creates `miner-config.json` with `attestation_enabled` and `auto_enroll` set to
`false`. Running `agent.py` only inspects `/health` and `/epoch`. The separate
`--show-activation-commands` flag prints `clawrtc` commands for review but does
not contact the node or execute them. Activation requires explicit user action.

```bash
uvx create-rustchain-agent my-miner --profile miner
cd my-miner
python agent.py
python agent.py --show-activation-commands
```

### `bottube-creator`

Creates a placeholder `.env.example`, a local `draft.json`, and an enforced
dry-run preview. The generated program contains no HTTP client or posting
implementation, refuses `BOTTUBE_DRY_RUN=false`, never prints an API key, and
warns against human account credentials.

```bash
uvx create-rustchain-agent my-creator --profile bottube-creator
cd my-creator
python agent.py
```

## What it generates

| File | Profiles | Purpose |
|------|----------|---------|
| `wallet.json` | all | Ed25519 RTC wallet (**private key inside; 0600 + gitignored**) |
| `agent.py` | all | safe default behavior for the selected profile |
| `.mcp.json` | all | runs `rustchain-mcp` with the selected `RUSTCHAIN_NODE` |
| `README.md` | all | profile-specific operation and security guidance |
| `.gitignore` | all | excludes `wallet.json`, `.env`, and Python cache files |
| `miner-config.json` | miner | disabled mining configuration and reviewable commands |
| `.env.example` | bottube-creator | placeholder agent environment values and dry-run setting |
| `draft.json` | bottube-creator | local placeholder video metadata |

## Safe by default

Scaffolding is local only: it generates files and a wallet, with no network
writes. Generated observer and miner programs perform read-only inspection;
the creator program makes no network requests at all.

`--register` is retained for backward compatibility and is the one generator
option that performs a network write. It registers a Beacon identity after
scaffolding and must always be supplied explicitly.

The generated `.mcp.json` uses the supported `RUSTCHAIN_NODE` environment
variable. It does not import `wallet.json`; `rustchain-mcp` maintains its own
encrypted keystore for wallet tools. Review and approve the project-scoped MCP
server when your editor prompts. Keep `wallet.json` private.

`--node` accepts only an absolute `http://` or `https://` URL with a valid host
and optional port. Userinfo credentials, query strings, fragments, control
characters, malformed ports, and unsafe path characters are rejected before
the project directory or wallet is created. Trailing slashes are normalized so
`agent.py` and `.mcp.json` always receive the same node value.

## Options

```text
--profile {observer,miner,bottube-creator}
             Generated behavior (default: observer)
--node URL   RustChain node used by agent.py and .mcp.json
--register   Register a Beacon identity after scaffolding (network write)
```

Part of the [RustChain](https://rustchain.org) ecosystem.

## Development

The test suite is offline: generated network clients use a loopback HTTP server,
and tests never register identities, enroll miners, attest, upload, or post.

```bash
python3 -m unittest discover -s tests -v
python3 -m create_rustchain_agent --help
```

## License

MIT (c) Elyan Labs.
