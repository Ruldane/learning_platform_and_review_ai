import { mcp } from "@/shared/i18n/messages/mcp";
import type {
  ActionView,
  CallView,
  ChangeView,
  ConfirmationView,
  FeatureOption,
  RequestView,
  TokenView,
  VerdictView,
} from "./components/viewTypes";
import type {
  McpActionOut,
  McpCallOut,
  McpChangeOut,
  McpConfirmationOut,
  McpFeatureOut,
  McpTokenOut,
} from "./types";

const isFeature = (key: string): key is keyof typeof mcp.features =>
  Object.hasOwn(mcp.features, key);

/** The name of a feature in French; an unknown feature keeps its raw name. */
export const featureLabel = (key: string): string => (isFeature(key) ? mcp.features[key] : key);

const passed = (iso: string, now: Date) => new Date(iso).getTime() <= now.getTime();

export function toTokenView(token: McpTokenOut, now: Date = new Date()): TokenView {
  const status = token.revoked_at
    ? "revoked"
    : passed(token.expires_at, now)
      ? "expired"
      : "active";
  return {
    id: token.id,
    label: token.label,
    features: token.features.map(featureLabel),
    mode: token.mode,
    status,
    expiresAt: token.expires_at,
    revokedAt: token.revoked_at,
    lastUsedAt: token.last_used_at,
  };
}

export function toFeatureOption(feature: McpFeatureOut): FeatureOption {
  return {
    id: feature.feature,
    label: featureLabel(feature.feature),
    read: feature.read_actions,
    write: feature.write_actions,
    confirm: feature.confirm_actions,
  };
}

/** The verdict, read without assumptions: a missing or malformed check never says "no caveats". */
export function toVerdict(precheck: McpConfirmationOut["precheck"]): VerdictView | null {
  if (!precheck || typeof precheck !== "object") return null;
  const reasons = Array.isArray(precheck.reasons)
    ? precheck.reasons.filter((reason): reason is string => typeof reason === "string")
    : [];
  const summary = typeof precheck.summary === "string" ? precheck.summary : null;
  return { ok: precheck.ok === true, reasons, summary };
}

export function toRequestView(request: McpConfirmationOut["request"]): RequestView {
  return {
    method: request.method,
    route: request.route,
    targetLabel: request.target_label,
    fields: request.fields.map((field) => ({
      name: field.name,
      value: field.value_preview === "" ? null : field.value_preview,
    })),
    truncated: request.truncated,
  };
}

export function toConfirmationView(
  confirmation: McpConfirmationOut,
  tokenLabels: ReadonlyMap<string, string>,
  now: Date = new Date(),
): ConfirmationView {
  const lapsed = confirmation.status === "pending" && passed(confirmation.expires_at, now);
  return {
    id: confirmation.id,
    summary: confirmation.summary,
    action: confirmation.action,
    tokenLabel: tokenLabels.get(confirmation.token_id) ?? null,
    state: lapsed ? "expired" : confirmation.status,
    expiresAt: confirmation.expires_at,
    decidedAt: confirmation.decided_at,
    verdict: toVerdict(confirmation.precheck),
    request: toRequestView(confirmation.request),
  };
}

/** Requests still open: pending, and whose deadline has not passed. */
export const isOpen = (confirmation: McpConfirmationOut, now: Date = new Date()) =>
  confirmation.status === "pending" && !passed(confirmation.expires_at, now);

export const toCallView = (
  call: McpCallOut,
  tokenLabels: ReadonlyMap<string, string>,
): CallView => ({
  id: call.id,
  at: call.created_at,
  action: call.action,
  tokenLabel: (call.token_id && tokenLabels.get(call.token_id)) || null,
  level: call.level,
  code: call.code,
  durationMs: call.duration_ms,
});

export const toChangeView = (change: McpChangeOut): ChangeView => ({
  callId: change.call_id,
  at: change.created_at,
  action: change.action,
  rows: change.rows,
  tables: change.tables,
  undoneAt: change.undone_at,
});

export const toActionView = (action: McpActionOut): ActionView => ({
  name: action.name,
  feature: action.feature,
  featureLabel: featureLabel(action.feature),
  kind: action.kind,
  level: action.level,
  summary: action.summary,
  external: action.side_effects === "external",
  untrusted: action.untrusted.length > 0,
});
