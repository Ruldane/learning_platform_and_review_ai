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

/** Un champ de la requête à confirmer ; `value` nul : la valeur n'est pas montrée (aperçu coupé). */
export interface RequestFieldView {
  name: string;
  value: string | null;
}

/** La requête qui partira à la confirmation, lue en entier. Les textes sont affichés comme texte. */
export interface RequestView {
  method: string;
  route: string;
  /** Libellé de la cible ; un texte venu du web y est entouré de `<donnee_non_fiable>`. */
  targetLabel: string | null;
  fields: RequestFieldView[];
  truncated: boolean;
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
  request: RequestView;
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
