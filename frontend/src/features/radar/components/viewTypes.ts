/**
 * Types de vue du radar du marché : une copie réduite de `RadarRunOut` (`GET /radar/runs/{id}`,
 * `GET /radar/latest`) avec les seuls champs que les composants lisent. Les pages (8.14)
 * convertissent les réponses vers ces formes.
 */

/** `TrendOut` : une compétence du classement et son évolution depuis le relevé précédent. */
export interface SkillTrendView {
  rank: number;
  skill: string;
  /** La part des offres analysées qui la demandent, entre 0 et 1. */
  share: number;
  /** Points de pourcentage gagnés ou perdus ; `null` sans relevé précédent. */
  deltaShare: number | null;
  /** Absente du relevé précédent (jamais vrai au premier relevé). */
  isNew: boolean;
}

export interface BlockedDomainView {
  domain: string;
  count: number;
}

/** Le décompte d'un relevé : ce qui a réellement été lu, bloqué et analysé. */
export interface RunSummaryView {
  role: string;
  zone: string;
  readCount: number;
  blockedCount: number;
  analyzed: number;
  /** Pages lues qui n'étaient pas des offres. */
  notPostings: number;
  blockedDomains: BlockedDomainView[];
  /** Moins de 30 offres lisibles : le classement est indicatif. */
  lowSample: boolean;
}

/** `RadarAlertOut` : une compétence très demandée et absente du programme. */
export interface RadarAlertView {
  skill: string;
  share: number;
  /** Le message écrit par le serveur, déjà en français. */
  message: string;
}

/** `OfferOut` : une offre lue, avec son score de match calculé par le code. */
export interface RadarOfferView {
  title: string | null;
  company: string | null;
  url: string;
  score: number;
  level: string;
  remote: string | null;
  salary: string | null;
}

/** Le formulaire de lancement : poste et zone saisis, la zone vide laissant le défaut du serveur. */
export interface RadarRunRequestView {
  role: string;
  zone: string | null;
}
