"""Back-end scheduled tasks (D91): APScheduler in the server loop, opened by the lifespan after the
agent engine. One more task = one `JobSpec` in `registry.JOBS`. No feature and no engine imports
this package (import contract 8)."""
