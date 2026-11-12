import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SourcesViewModel, SourceView } from "../sourceTypes";
import { SourcesPanel } from "./SourcesPanel";

const base: SourceView = {
  id: "src1",
  url: "https://exemple.fr/guide-rag",
  title: "Guide du RAG",
  author: "Awa Diallo",
  date: "2026-03-04",
  lang: "fr",
  score: 82,
  status: "ok",
  verdict: "kept",
  reason: null,
  kind: "page",
  role: null,
};

const model: SourcesViewModel = {
  queries: [
    { id: "q1", text: "évaluation d'un RAG", lang: "fr", summary: "8 résultats", ok: true },
    { id: "q2", text: "rag evaluation", lang: "en", summary: null, ok: null },
  ],
  kept: [base],
  rejected: [
    {
      ...base,
      id: "src2",
      title: "Billet de blog",
      score: 41,
      verdict: "rejected",
      reason: "Contenu trop superficiel.",
    },
  ],
  unreadable: [
    {
      ...base,
      id: "src3",
      title: "Page vide",
      score: null,
      status: "unreadable",
      verdict: null,
      reason: "Page illisible : aucun texte principal trouvé.",
    },
  ],
  people: [
    {
      ...base,
      id: "p1",
      title: "Ada Lovelace",
      url: "https://exemple.fr/ada",
      kind: "person",
      role: "Ingénieure ML",
      score: null,
    },
  ],
};

const none: SourcesViewModel = { queries: [], kept: [], rejected: [], unreadable: [], people: [] };

describe("SourcesPanel", () => {
  it("groups kept, rejected and unreadable sources", () => {
    render(<SourcesPanel model={model} pending={false} />);
    const kept = screen.getByRole("region", { name: "Retenues" });
    expect(within(kept).getByText("82/100")).toBeInTheDocument();
    const rejected = screen.getByRole("region", { name: "Écartées" });
    expect(within(rejected).getByText("Contenu trop superficiel.")).toBeInTheDocument();
    const unreadable = screen.getByRole("region", { name: "Illisibles" });
    expect(within(unreadable).getByText("Page vide")).toBeInTheDocument();
    expect(within(unreadable).queryByRole("link")).toBeNull();
  });

  it("lists the practitioners found apart from the pages", () => {
    render(<SourcesPanel model={model} pending={false} />);
    const people = screen.getByRole("region", { name: "Praticiens repérés" });
    expect(within(people).getByRole("link", { name: "Ada Lovelace" })).toHaveAttribute(
      "href",
      "https://exemple.fr/ada",
    );
    expect(within(people).getByText("Ingénieure ML")).toBeInTheDocument();
    expect(within(people).getByText("Publie sur exemple.fr")).toBeInTheDocument();
    expect(within(people).queryByText(/\/100/)).toBeNull();
    const kept = screen.getByRole("region", { name: "Retenues" });
    expect(within(kept).queryByText("Ada Lovelace")).toBeNull();
  });

  it("is not empty when only practitioners were found", () => {
    render(<SourcesPanel model={{ ...none, people: model.people }} pending={false} />);
    expect(screen.queryByText("Aucune source pour l'instant.")).toBeNull();
  });

  it("shows the queries that were sent with their language", () => {
    render(<SourcesPanel model={model} pending={false} />);
    const queries = screen.getByRole("region", { name: "Requêtes lancées" });
    expect(within(queries).getByText("rag evaluation")).toBeInTheDocument();
    expect(within(queries).getByText("en")).toBeInTheDocument();
    expect(within(queries).getByText("8 résultats")).toBeInTheDocument();
    expect(within(queries).getAllByRole("listitem")).toHaveLength(2);
  });

  it("says when a query failed", () => {
    const query = { id: "q", text: "x", lang: null, summary: null, ok: false };
    render(<SourcesPanel model={{ ...none, queries: [query] }} pending={false} />);
    expect(screen.getByText("Sans réponse")).toBeInTheDocument();
  });

  it("omits the blocks that have nothing in them", () => {
    render(<SourcesPanel model={{ ...none, kept: [base] }} pending={false} />);
    expect(screen.getByRole("region", { name: "Retenues" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Écartées" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Illisibles" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Requêtes lancées" })).toBeNull();
  });

  it("shows an empty state when nothing was found yet", () => {
    render(<SourcesPanel model={none} pending={false} />);
    expect(screen.getByText("Aucune source pour l'instant.")).toBeInTheDocument();
  });

  it("announces that the Éclaireur is searching, politely", () => {
    render(<SourcesPanel model={none} pending />);
    const status = screen.getByText("L'Éclaireur cherche…");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(screen.queryByText("Aucune source pour l'instant.")).toBeNull();
  });
});
