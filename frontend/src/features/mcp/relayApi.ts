import { api } from "@/shared/api/client";
import { ApiError, unwrap } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";

const LOCAL_PAIRING_URL = "http://127.0.0.1:8770/pair";

export async function fetchRelayStatus(signal?: AbortSignal) {
  return unwrap(await api.GET("/mcp/relay/status", { signal }));
}

export async function pairRelay(): Promise<void> {
  const { code } = unwrap(await api.POST("/mcp/relay/pairing"));
  const response = await fetch(LOCAL_PAIRING_URL, {
    method: "POST",
    credentials: "omit",
    redirect: "error",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
    signal: AbortSignal.timeout(12_000),
  }).catch(() => null);
  if (response?.status === 204) return;
  throw new ApiError({
    status: response?.status ?? 0,
    code: "relay_pairing_failed",
    message: t(response?.status === 409 ? "mcp.relay.refused" : "mcp.relay.unavailable"),
  });
}

export async function revokeRelay(): Promise<void> {
  unwrap(await api.DELETE("/mcp/relay/pairing"));
}
