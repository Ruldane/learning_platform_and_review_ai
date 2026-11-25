/**
 * View types for the sources panel (D34): the panel knows neither the API nor the events;
 * the page using it converts its data into these shapes.
 */

/** A page found by the web search, or a practitioner found (`kind: "person"`, SPEC 10.3). */
export interface SourceView {
  id: string;
  /** `person`: a practitioner (the title is their name, the address a profile or publication). */
  kind: "page" | "person";
  url: string;
  title: string;
  /** A practitioner's role (« Ingénieure ML chez… »); `null` for a page. */
  role: string | null;
  author: string | null;
  /** Publication date, as ISO (`2026-03-04`) or free text. */
  date: string | null;
  /** Language code (`fr`, `en`). */
  lang: string | null;
  /** Score out of 100; `null` until the page is rated (or if unreadable). */
  score: number | null;
  /** `unreadable`: no main text could be read; the page is never cited. */
  status: "ok" | "unreadable";
  verdict: "kept" | "rejected" | null;
  /** Why the page is discarded or unreadable. */
  reason: string | null;
}

/** A web search query that was run. */
export interface QueryView {
  id: string;
  text: string;
  lang: string | null;
  /** Summary of the result (« 8 résultats »), once the search is finished. */
  summary: string | null;
  /** `null`: still running. */
  ok: boolean | null;
}

export interface SourcesViewModel {
  queries: QueryView[];
  kept: SourceView[];
  rejected: SourceView[];
  unreadable: SourceView[];
  /** Practitioners found, shown apart from the pages. */
  people: SourceView[];
}
