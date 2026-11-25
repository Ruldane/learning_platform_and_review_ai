import { t } from "@/shared/i18n/t";
import type { EventOf, SessionEvent } from "@/shared/realtime/types";
import type { QueryView, SourcesViewModel, SourceView } from "./sourceTypes";

const SEARCH_TOOL = "web_search";

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

/** Replayed queries (resumed node) have the same language and text: one line only. */
interface Queries {
  byKey: Map<string, QueryView>;
  keyOfCall: Map<string, string>;
}

function addQuery({ byKey, keyOfCall }: Queries, event: EventOf<"tool.called">) {
  const { call_id, args } = event.payload;
  const query = text(args.query);
  const lang = text(args.lang);
  // A failed search does not emit its query (D77): it keeps its line, under the call.
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
    // An event stored before D82 has no `kind`: it is a page.
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
 * Converts the events of a web search session into the SourcesPanel model (D34).
 * A source is identified by its `source_id` (its address if it has none: excluded domain):
 * a replayed node re-emits its `source.found` (D77), the last event wins. A page read but
 * not yet judged is not shown (the contract does not emit this case). Practitioners (`kind:
 * "person"`) form a separate block, without a score: they are shown unless discarded.
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
      // A page and a practitioner never replace each other, even with the same address.
      sources.set(`${source.kind}:${source.id}`, source);
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
