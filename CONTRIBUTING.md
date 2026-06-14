# Contributing to create-rustchain-agent

Thanks for helping make RustChain onboarding faster. This document is intentionally short — `create-rustchain-agent` is a small scaffolding CLI, so most contributions are surgical.

## Where to start

| Goal | File to touch |
|------|---------------|
| Add or change a generated file (e.g. `agent.py`, `wallet.json`) | `create_rustchain_agent/` package source |
| Add or change a CLI flag (e.g. `--register`, `--node`) | `__main__.py` + update this CONTRIBUTING + the README |
| Bump the version | `pyproject.toml` (`[project] version = ...`) + a Git tag |
| Change project metadata / homepage | `pyproject.toml` (`[project.urls]`) |
| Change install / quick-start commands | `README.md` |

## Development setup

```bash
# Clone your fork
git clone https://github.com/<you>/create-rustchain-agent
cd create-rustchain-agent

# Recommended: uv (fast, isolated)
uv venv
uv pip install -e ".[dev]"

# Or: classic venv
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The dev extras currently include the package itself with `cryptography>=41.0`. Add a `tests/` extra if you introduce a `pytest` suite.

## Code style

- Python 3.8+ compatible (matches `pyproject.toml`'s `requires-python`).
- Use type hints where it improves clarity, but don't fight the dynamic generation code.
- No external runtime dependencies beyond `cryptography`.
- Keep the CLI surface small — flags, not subcommands, until the surface justifies it.

## Testing locally

There is no upstream test suite yet. When you add one, please keep the smoke checks in this order:

```bash
# 1. Import sanity
python -c "import create_rustchain_agent; print('ok')"

# 2. CLI sanity
python -m create_rustchain_agent --help

# 3. End-to-end scaffold (writes to a throwaway dir)
cd /tmp
python -m create_rustchain_agent smoketest-agent
ls smoketest-agent
rm -rf smoketest-agent
```

For destructive or network-touching changes, also confirm:

```bash
# 4. --node flag (testnet only — never mainnet during local dev)
python -m create_rustchain_agent smoketest-agent --node https://testnet.rustchain.org
```

## Pull request guidelines

1. **One change per PR.** A new flag, a docs fix, a bug fix — keep the diff focused.
2. **Update the README** if the change is user-visible. The README is the contract.
3. **Update this file** if you add a CLI flag, a new generated file, or a new dev dependency.
4. **Tag your commits** with a conventional prefix:
   - `feat:` new flag or generated file
   - `fix:` bug in the scaffold
   - `docs:` README / CONTRIBUTING / docstring only
   - `chore:` version bumps, dependency pins
5. **Link the issue** (if any) in the PR body.

## Security notes

- The scaffold generates a **real Ed25519 keypair** in `wallet.json`. The CLI sets `0600` perms and adds `wallet.json` to `.gitignore`. Do not weaken these defaults.
- `--register` performs a **network write** to the Beacon service. Never auto-run it; the user must opt in.
- The package has no telemetry, no analytics, and no background services.

## Release process

The maintainer (Elyan Labs) handles releases. A release is:

```bash
# Bump pyproject version
# Tag
git tag -a v0.x.y -m "v0.x.y"
git push --tags

# Build + publish (maintainer only)
python -m build
twine upload dist/*
```

## Code of Conduct

Be excellent to each other. This is a 60-second onboarding tool — keep the bar friendly and the cycle time short.

## License

By contributing, you agree that your contributions are licensed under the project's MIT License.
