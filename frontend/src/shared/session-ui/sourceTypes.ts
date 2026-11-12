/**
 * Types de vue du panneau des sources (D34) : le panneau ne connaît ni l'API ni les événements,
 * la page qui l'utilise convertit ses données dans ces formes.
 */

/** Une page trouvée par la recherche web, ou un praticien repéré (`kind: "person"`, SPEC 10.3). */
export interface SourceView {
  id: string;
  /** `person` : un praticien (le titre est son nom, l'adresse un profil ou une publication). */
  kind: "page" | "person";
  url: string;
  title: string;
  /** Rôle d'un praticien (« Ingénieure ML chez… ») ; `null` pour une page. */
  role: string | null;
  author: string | null;
  /** Date de publication, en ISO (`2026-03-04`) ou en texte libre. */
  date: string | null;
  /** Code de langue (`fr`, `en`). */
  lang: string | null;
  /** Note sur 100 ; `null` tant que la page n'est pas notée (ou si elle est illisible). */
  score: number | null;
  /** `unreadable` : aucun texte principal n'a pu être lu, la page n'est jamais citée. */
  status: "ok" | "unreadable";
  verdict: "kept" | "rejected" | null;
  /** Pourquoi la page est écartée ou illisible. */
  reason: string | null;
}

/** Une requête de recherche lancée. */
export interface QueryView {
  id: string;
  text: string;
  lang: string | null;
  /** Résumé du résultat (« 8 résultats »), une fois la recherche terminée. */
  summary: string | null;
  /** `null` : encore en cours. */
  ok: boolean | null;
}

export interface SourcesViewModel {
  queries: QueryView[];
  kept: SourceView[];
  rejected: SourceView[];
  unreadable: SourceView[];
  /** Praticiens repérés, présentés à part des pages. */
  people: SourceView[];
}
