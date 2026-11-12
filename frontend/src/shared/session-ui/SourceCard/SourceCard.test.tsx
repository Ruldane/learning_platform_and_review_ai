import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SourceView } from "../sourceTypes";
import { SourceCard } from "./SourceCard";

const kept: SourceView = {
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

const unreadable: SourceView = {
  ...kept,
  id: "src3",
  url: "https://exemple.fr/vide",
  title: "Page vide",
  author: null,
  date: null,
  score: null,
  status: "unreadable",
  verdict: null,
  reason: "Page illisible : aucun texte principal trouvé.",
};

describe("SourceCard", () => {
  it("links the title safely and shows score, author, date and language", () => {
    render(<SourceCard source={kept} />);
    const link = screen.getByRole("link", { name: "Guide du RAG" });
    expect(link).toHaveAttribute("href", "https://exemple.fr/guide-rag");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText("82/100")).toBeInTheDocument();
    expect(screen.getByText("Awa Diallo")).toBeInTheDocument();
    expect(screen.getByText("4 mars 2026")).toBeInTheDocument();
    expect(screen.getByText("fr")).toBeInTheDocument();
  });

  it("does not repeat a reason on a kept source", () => {
    render(<SourceCard source={{ ...kept, reason: "Bonne source." }} />);
    expect(screen.queryByText("Bonne source.")).toBeNull();
  });

  it("shows the reason of a rejected source, still linked", () => {
    const rejected: SourceView = {
      ...kept,
      score: 41,
      verdict: "rejected",
      reason: "Contenu trop superficiel.",
    };
    render(<SourceCard source={rejected} />);
    expect(screen.getByText("Contenu trop superficiel.")).toBeInTheDocument();
    expect(screen.getByText("41/100")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Guide du RAG" })).toBeInTheDocument();
  });

  it("never links an unreadable page", () => {
    render(<SourceCard source={{ ...unreadable }} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Page vide")).toBeInTheDocument();
    expect(screen.getByText("Page illisible : aucun texte principal trouvé.")).toBeInTheDocument();
    expect(screen.queryByText(/\/100/)).toBeNull();
  });

  it("does not link an address that is not http(s)", () => {
    render(<SourceCard source={{ ...kept, url: "javascript:alert(1)" }} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Guide du RAG")).toBeInTheDocument();
  });

  it("prints an unparseable date as it came", () => {
    render(<SourceCard source={{ ...kept, date: "printemps 2026" }} />);
    expect(screen.getByText("printemps 2026")).toBeInTheDocument();
  });
});
