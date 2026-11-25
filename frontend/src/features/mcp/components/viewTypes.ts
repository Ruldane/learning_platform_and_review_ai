export type TokenStatus = "active" | "expired" | "revoked";
export type TokenMode = "read" | "write";
export type ExpiryDays = 1 | 7 | 30 | 90;
export type ToolLevel = 1 | 2 | 3;
/** A log call; 0: refused before even finding the tool. */
export type CallLevel = 0 | ToolLevel;

export const EXPIRY_CHOICES: readonly ExpiryDays[] = [1, 7, 30, 90];

export interface TokenView {
  id: string;
  label: string;
  /** The open features, in French (an unknown name stays raw). */
  features: string[];
  mode: TokenMode;
  status: TokenStatus;
  expiresAt: string;
  revokedAt: string | null;
  lastUsedAt: string | null;
}

/** What creation returns, shown only once. */
export interface RevealedToken {
  token: string;
  label: string;
}

export interface FeatureOption {
  id: string;
  label: string;
  read: number;
  write: number;
  confirm: number;
}

/** What the form sends. */
export interface TokenDraft {
  label: string;
  features: string[];
  mode: TokenMode;
  expiresInDays: ExpiryDays;
}

export type ConfirmationState = "pending" | "confirmed" | "refused" | "expired" | "failed";

/** The pre-check verdict; `ok` is true only if the check said so in full. */
export interface VerdictView {
  ok: boolean;
  reasons: string[];
  summary: string | null;
}

/** A field of the request to confirm; `value` null: the value is not shown (cut preview). */
export interface RequestFieldView {
  name: string;
  value: string | null;
}

/** The request that will run on confirmation, read in full. Texts are shown as text. */
export interface RequestView {
  method: string;
  route: string;
  /** Label of the target; a text from the web is wrapped in `<donnee_non_fiable>`. */
  targetLabel: string | null;
  fields: RequestFieldView[];
  truncated: boolean;
}

export interface ConfirmationView {
  id: string;
  summary: string;
  action: string;
  tokenLabel: string | null;
  /** `expired` also when the deadline has passed without the server having noted it yet. */
  state: ConfirmationState;
  expiresAt: string;
  decidedAt: string | null;
  verdict: VerdictView | null;
  request: RequestView;
}

export interface CallView {
  id: string;
  at: string;
  action: string;
  /** The token name; `null`: the presented token does not exist. */
  tokenLabel: string | null;
  level: CallLevel;
  code: number;
  durationMs: number;
}

export interface ChangeView {
  callId: string;
  at: string;
  action: string;
  rows: number;
  tables: string[];
  undoneAt: string | null;
}

export interface ActionView {
  name: string;
  feature: string;
  featureLabel: string;
  kind: "route" | "graph";
  level: ToolLevel;
  summary: string | null;
  /** Touches something other than the database: always to confirm. */
  external: boolean;
  /** Part of the answer comes from the web: rendered as data. */
  untrusted: boolean;
}
