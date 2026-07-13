"""Safe, profile-based onboarding for a RustChain-participating agent.

Scaffolds an Ed25519 RTC wallet, profile-specific agent behavior and guidance,
and an MCP config wiring rustchain-mcp through RUSTCHAIN_NODE. Observer remains
the backward-compatible default; miner and BoTTube creator profiles are opt-in.

Scaffolding is local only. A Beacon registration network write happens only
when the user explicitly supplies --register.
"""

__version__ = "0.1.0"
