export type TokenStatus = "active" | "expired" | "revoked";
export type TokenMode = "read" | "write";
export type ExpiryDays = 1 | 7 | 30 | 90;
export type ToolLevel = 1 | 2 | 3;
/** Un appel du journal ; 0 : refusé avant même de trouver l'outil. */
export type CallLevel = 0 | ToolLevel;

export const EXPIRY_CHOICES: readonly ExpiryDays[] = [1, 7, 30, 90];

export interface TokenView {
  id: string;
  label: string;
  /** Les features ouvertes, en français (un nom inconnu reste brut). */
  features: string[];
  mode: TokenMode;
  status: TokenStatus;
  expiresAt: string;
  revokedAt: string | null;
  lastUsedAt: string | null;
}

/** Ce que la création renvoie, et qu'on ne montre qu'une fois. */
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

/** Ce que le formulaire envoie. */
export interface TokenDraft {
  label: string;
  features: string[];
  mode: TokenMode;
  expiresInDays: ExpiryDays;
}

export type ConfirmationState = "pending" | "confirmed" | "refused" | "expired" | "failed";

/** Le verdict du contrôle préalable ; `ok` n'est vrai que si le contrôle l'a dit en toutes lettres. */
export interface VerdictView {
  ok: boolean;
  reasons: string[];
  summary: string | null;
}

export interface ConfirmationView {
  id: string;
  summary: string;
  action: string;
  tokenLabel: string | null;
  /** `expired` aussi quand l'échéance est passée sans que le serveur l'ait encore noté. */
  state: ConfirmationState;
  expiresAt: string;
  decidedAt: string | null;
  verdict: VerdictView | null;
}

export interface CallView {
  id: string;
  at: string;
  action: string;
  /** Le nom du jeton ; `null` : le jeton présenté n'existe pas. */
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
  /** Touche autre chose que la base : toujours à confirmer. */
  external: boolean;
  /** Une partie de la réponse vient du web : rendue comme donnée. */
  untrusted: boolean;
}
