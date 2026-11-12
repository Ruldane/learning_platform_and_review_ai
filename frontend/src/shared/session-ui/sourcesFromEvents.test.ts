import { describe, expect, it } from "vitest";
import { researchEvents } from "@/test/researchEvents";
import { sourcesFromEvents } from "./sourcesFromEvents";

const { toolCalled, toolResult, sourceFound } = researchEvents();

describe("sourcesFromEvents", () => {
  it("classifies kept, rejected and unreadable", () => {
    const model = sourcesFromEvents([
      toolCalled("c1", "web_search", { query: "rag", lang: "en" }),
      toolResult("c1", true, "8 résultat(s) via searxng"),
      sourceFound({ source_id: "a", score: 82, verdict: "kept" }),
      sourceFound({
        source_id: "b",
        score: 41,
        verdict: "rejected",
        reason: "Trop superficielle.",
      }),
      sourceFound({ source_id: "c", status: "unreadable", reason: "Page injoignable." }),
    ]);
    expect(model).toMatchObject({
      queries: [{ text: "rag", lang: "en", summary: "8 résultat(s) via searxng", ok: true }],
      kept: [{ id: "a", score: 82 }],
      rejected: [{ id: "b", reason: "Trop superficielle." }],
      unreadable: [{ id: "c", status: "unreadable" }],
    });
  });

  it("keeps a query pending until its result arrives and ignores other tools", () => {
    const model = sourcesFromEvents([
      toolCalled("c1", "web_search", { query: "rag", lang: "fr" }),
      toolCalled("c2", "web_read", { url: "https://exemple.fr/a" }),
      toolResult("c2", true, "Lue", "web_read"),
    ]);
    expect(model.queries).toEqual([
      { id: expect.any(String), text: "rag", lang: "fr", summary: null, ok: null },
    ]);
  });

  it("shows a failed search whose query was never emitted", () => {
    const model = sourcesFromEvents([
      toolCalled("c1", "web_search", { lang: "fr" }),
      toolResult("c1", false, "Aucun moteur de recherche n'a répondu."),
    ]);
    expect(model.queries).toMatchObject([
      { lang: "fr", ok: false, summary: "Aucun moteur de recherche n'a répondu." },
    ]);
    expect(model.queries[0]?.text).not.toBe("");
  });

  it("merges a replayed node: same query and same source_id, the latest wins", () => {
    const model = sourcesFromEvents([
      toolCalled("c1", "web_search", { query: "rag", lang: "fr" }),
      toolResult("c1", true, "8 résultat(s) via searxng"),
      sourceFound({ source_id: "a", status: "unreadable", reason: "Page injoignable." }),
      toolCalled("c9", "web_search", { query: "rag", lang: "fr" }),
      toolResult("c9", true, "8 résultat(s) via searxng"),
      sourceFound({ source_id: "a", score: 70, verdict: "kept" }),
    ]);
    expect(model.queries).toHaveLength(1);
    expect(model.unreadable).toEqual([]);
    expect(model.kept).toMatchObject([{ id: "a", score: 70 }]);
  });

  it("keeps excluded-domain pages (no source_id) as unreadable, keyed by their url", () => {
    const reason = "Domaine exclu dans les réglages.";
    const model = sourcesFromEvents([
      sourceFound({ url: "https://pinterest.com/x", status: "unreadable", reason }),
      sourceFound({ url: "https://pinterest.com/y", status: "unreadable", reason }),
    ]);
    expect(model.unreadable.map((s) => s.id)).toEqual([
      "https://pinterest.com/x",
      "https://pinterest.com/y",
    ]);
  });

  it("does not show a page that is read but not judged yet", () => {
    const model = sourcesFromEvents([sourceFound({ source_id: "a" })]);
    expect(model).toEqual({ queries: [], kept: [], rejected: [], unreadable: [], people: [] });
  });

  it("maps the payload to the view, with an empty title falling back to the url", () => {
    const model = sourcesFromEvents([
      sourceFound({
        source_id: "a",
        verdict: "kept",
        score: 90,
        title: "",
        author: "Ada",
        date: "2026-03-04",
        lang: "en",
      }),
    ]);
    expect(model.kept[0]).toEqual({
      id: "a",
      url: "https://exemple.fr/a",
      title: "https://exemple.fr/a",
      author: "Ada",
      date: "2026-03-04",
      lang: "en",
      score: 90,
      status: "ok",
      verdict: "kept",
      reason: null,
      kind: "page",
      role: null,
    });
  });

  it("puts people apart", () => {
    const model = sourcesFromEvents([
      sourceFound({
        source_id: "p1",
        kind: "person",
        role: "Ingénieure ML",
        title: "Ada Lovelace",
        url: "https://exemple.fr/ada",
        verdict: "kept",
        score: 80,
      }),
      sourceFound({ source_id: "a", verdict: "kept", score: 90 }),
    ]);
    expect(model.people).toMatchObject([
      { id: "p1", title: "Ada Lovelace", kind: "person", role: "Ingénieure ML" },
    ]);
    expect(model.kept.map((s) => s.id)).toEqual(["a"]);
  });

  it("keeps a page and a practitioner that share an address apart (no source_id)", () => {
    const model = sourcesFromEvents([
      sourceFound({
        url: "https://exemple.fr/ada",
        title: "Un article",
        verdict: "kept",
        score: 80,
      }),
      sourceFound({ url: "https://exemple.fr/ada", title: "Ada", kind: "person", role: "ML" }),
    ]);
    expect(model.kept.map((s) => s.title)).toEqual(["Un article"]);
    expect(model.people.map((s) => s.title)).toEqual(["Ada"]);
  });

  it("shows a person who was not judged but not a rejected one", () => {
    const model = sourcesFromEvents([
      sourceFound({ source_id: "p1", kind: "person", title: "Ada" }),
      sourceFound({ source_id: "p2", kind: "person", title: "Bob", verdict: "rejected" }),
    ]);
    expect(model.people.map((p) => p.title)).toEqual(["Ada"]);
  });

  it("reads an old event without kind as a page", () => {
    const old = sourceFound({ source_id: "a", verdict: "kept", score: 50 });
    if (old.type === "source.found") {
      delete (old.payload as Partial<typeof old.payload>).kind;
    }
    expect(sourcesFromEvents([old]).kept).toHaveLength(1);
  });
});
