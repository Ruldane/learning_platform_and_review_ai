"""MCP server engine (phase 10, P10 to P19): this is not a feature. Each feature declares its
actions in `features/<f>/mcp.py` (`MCP: FeatureMcp`); the `MCP_FEATURES` registry assembles
them. This package imports no feature nor `app.agents` (import contract 9): it only knows the
declarations (`base`) and calls the application's real route."""
