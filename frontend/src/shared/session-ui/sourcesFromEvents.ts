import { t } from "@/shared/i18n/t";
import type { EventOf, SessionEvent } from "@/shared/realtime/types";
import type { QueryView, SourcesViewModel, SourceView } from "./sourceTypes";

const SEARCH_TOOL = "web_search";

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

/** Les requêtes rejouées (nœud repris) ont la même langue et le même texte : une seule ligne. */
interface Queries {
  byKey: Map<string, QueryView>;
  keyOfCall: Map<string, string>;
}

function addQuery({ byKey, keyOfCall }: Queries, event: EventOf<"tool.called">) {
  const { call_id, args } = event.payload;
  const query = text(args.query);
  const lang = text(args.lang);
  // Une recherche en échec n'émet pas sa requête (D77) : elle garde sa ligne, sous l'appel.
  const key = query ? `${lang ?? ""}|${query}` : call_id;
  keyOfCall.set(call_id, key);
  const previous = byKey.get(key);
  byKey.set(key, {
    id: key,
    text: query ?? t("session.sources.queryHidden"),
    lang,
    summary: previous?.summary ?? null,
    ok: previous?.ok ?? null,
  });
}

function addResult({ byKey, keyOfCall }: Queries, event: EventOf<"tool.result">) {
  const key = keyOfCall.get(event.payload.call_id);
  const query = key === undefined ? undefined : byKey.get(key);
  if (key === undefined || !query) return;
  byKey.set(key, { ...query, summary: event.payload.summary, ok: event.payload.ok });
}

function toSource(event: EventOf<"source.found">): SourceView {
  const p = event.payload;
  return {
    id: p.source_id ?? p.url,
    // Un événement stocké avant D82 n'a pas de `kind` : c'est une page.
    kind: p.kind === "person" ? "person" : "page",
    url: p.url,
    title: p.title.trim() === "" ? p.url : p.title,
    role: p.role ?? null,
    author: p.author,
    date: p.date,
    lang: p.lang,
    score: p.score,
    status: p.status,
    verdict: p.verdict,
    reason: p.reason,
  };
}

/**
 * Convertit les événements d'une session de recherche web en modèle du `SourcesPanel` (D34).
 * Une source est identifiée par son `source_id` (son adresse si elle n'en a pas : domaine exclu) :
 * un nœud rejoué réémet ses `source.found` (D77), le dernier événement l'emporte. Une page lue mais
 * pas encore jugée n'est pas montrée (le contrat n'émet pas ce cas). Les praticiens (`kind:
 * "person"`) forment un bloc à part, sans note : ils sont montrés sauf s'ils sont écartés.
 */
export function sourcesFromEvents(events: SessionEvent[]): SourcesViewModel {
  const queries: Queries = { byKey: new Map(), keyOfCall: new Map() };
  const sources = new Map<string, SourceView>();
  for (const event of events) {
    if (event.type === "tool.called" && event.payload.tool === SEARCH_TOOL) {
      addQuery(queries, event);
    } else if (event.type === "tool.result" && event.payload.tool === SEARCH_TOOL) {
      addResult(queries, event);
    } else if (event.type === "source.found") {
      const source = toSource(event);
      sources.set(source.id, source);
    }
  }
  const all = [...sources.values()];
  const pages = all.filter((s) => s.kind === "page");
  return {
    queries: [...queries.byKey.values()],
    kept: pages.filter((s) => s.status === "ok" && s.verdict === "kept"),
    rejected: pages.filter((s) => s.status === "ok" && s.verdict === "rejected"),
    unreadable: pages.filter((s) => s.status === "unreadable"),
    people: all.filter((s) => s.kind === "person" && s.status === "ok" && s.verdict !== "rejected"),
  };
}
