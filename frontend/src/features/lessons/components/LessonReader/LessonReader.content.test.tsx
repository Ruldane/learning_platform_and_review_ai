import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LessonView } from "../viewTypes";
import { LessonReader } from "./LessonReader";

vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const lesson = (markdown: string): LessonView => ({
  title: "Les boucles en Python",
  markdown,
  wordCount: 1500,
  pdfUrl: null,
});

describe("LessonReader : contenu", () => {
  it("shows an unclosed raw HTML block as text and keeps the sections after it", () => {
    const markdown = [
      "## Objectifs",
      "- a",
      "<pre>",
      "x",
      "## Explication",
      "Long texte important.",
      "## Sources",
    ].join("\n");
    render(<LessonReader lesson={lesson(markdown)} />);
    const body = screen.getByTestId("lesson-body");
    expect(body).toHaveTextContent("Explication");
    expect(body).toHaveTextContent("Long texte important.");
    expect(body).toHaveTextContent("<pre>");
    // Du texte, jamais une balise interprétée.
    expect(body.querySelector("pre")).toBeNull();
  });

  it("never interprets a raw HTML block, even with a handler", () => {
    render(<LessonReader lesson={lesson('<div onclick="alert(1)">Bonjour</div>\n\nSuite.')} />);
    const body = screen.getByTestId("lesson-body");
    expect(body).toHaveTextContent('<div onclick="alert(1)">Bonjour</div>');
    expect(body.querySelector("[onclick]")).toBeNull();
    expect(body.querySelector("div")).toBeNull();
    expect(screen.getByText("Suite.")).toBeInTheDocument();
  });

  it("still drops inline HTML inside a paragraph", () => {
    render(<LessonReader lesson={lesson('Du texte <b onclick="x()">gras</b> ici.')} />);
    const body = screen.getByTestId("lesson-body");
    expect(body.querySelector("b")).toBeNull();
    expect(body).not.toHaveTextContent("<b");
    expect(body).toHaveTextContent("Du texte gras ici.");
  });

  it("shows the lesson title once: the page heading, not the Markdown one again", () => {
    render(
      <LessonReader
        lesson={lesson("# Les boucles en Python\n\n## Objectifs\n\nSavoir.\n\n# Annexe\n\nFin.")}
      />,
    );
    expect(screen.getAllByRole("heading", { name: "Les boucles en Python" })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Les boucles en Python");
    // Un titre de premier niveau placé après une section reste (en titre de section).
    expect(screen.getByRole("heading", { name: "Annexe" })).toBeInTheDocument();
  });
});
