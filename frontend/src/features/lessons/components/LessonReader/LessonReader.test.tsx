import { render, screen, within } from "@testing-library/react";
import mermaid from "mermaid";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { LessonView } from "../viewTypes";
import { LessonReader } from "./LessonReader";

vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const LESSON: LessonView = {
  title: "Les boucles en Python",
  markdown: [
    "## Objectifs",
    "",
    "Savoir écrire une boucle `for`.",
    "",
    "## Explication",
    "",
    "### Boucle for",
    "",
    "Du texte avec un [lien sûr](https://docs.python.org/3/) et du **gras**.",
    "",
    "| a | b |",
    "| - | - |",
    "| 1 | 2 |",
    "",
    "```python",
    "# Objectifs (ne doit pas devenir un titre)",
    "for i in range(3): print(i)",
    "```",
    "",
    "## Objectifs",
  ].join("\n"),
  wordCount: 1840,
  pdfUrl: "/api/lessons/l1/pdf",
};

function lesson(markdown: string, rest: Partial<LessonView> = {}): LessonView {
  return { ...LESSON, markdown, ...rest };
}

beforeEach(() => {
  vi.mocked(mermaid.initialize).mockClear();
  vi.mocked(mermaid.render).mockReset();
});

describe("LessonReader", () => {
  it("ignores raw HTML and javascript links", () => {
    render(<LessonReader lesson={lesson("<script>x</script> [a](javascript:alert(1))")} />);
    expect(document.querySelector("script")).toBeNull();
    expect(screen.queryByRole("link", { name: "a" })).toBeNull();
  });

  it("keeps the text of a link whose address is refused, without the link", () => {
    render(<LessonReader lesson={lesson("<script>x</script>\n\n[a](javascript:alert(1))")} />);
    expect(document.querySelector("script")).toBeNull();
    expect(screen.queryByRole("link", { name: "a" })).toBeNull();
    expect(screen.getByText("a")).toBeInTheDocument();
  });

  it("drops raw HTML elements and event handlers", () => {
    render(
      <LessonReader
        lesson={lesson('<img src="x" onerror="alert(1)"> <b onclick="x()">gras</b>')}
      />,
    );
    expect(document.querySelector("img")).toBeNull();
    expect(document.querySelector("[onclick]")).toBeNull();
  });

  it("keeps http and https links and opens them safely", () => {
    render(
      <LessonReader lesson={lesson("[docs](https://docs.python.org/3/) [mail](mailto:a@b.fr)")} />,
    );
    const link = screen.getByRole("link", { name: "docs" });
    expect(link).toHaveAttribute("href", "https://docs.python.org/3/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(screen.queryByRole("link", { name: "mail" })).toBeNull();
  });

  it("does not load remote images, it shows their description", () => {
    render(<LessonReader lesson={lesson("![schéma de la boucle](https://exemple.org/a.png)")} />);
    expect(document.querySelector("img")).toBeNull();
    expect(screen.getByText("Image non affichée : schéma de la boucle")).toBeInTheDocument();
  });

  it("builds a table of contents from sections", () => {
    render(<LessonReader lesson={LESSON} />);
    const toc = screen.getByRole("navigation", { name: "Sommaire" });
    const links = within(toc).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "Objectifs",
      "Explication",
      "Boucle for",
      "Objectifs",
    ]);
    const heading = screen.getByRole("heading", { name: "Boucle for" });
    expect(links[2]).toHaveAttribute("href", `#${heading.id}`);
    expect(new Set(links.map((link) => link.getAttribute("href"))).size).toBe(4);
  });

  it("renders mermaid blocks through MermaidSvg", async () => {
    vi.mocked(mermaid.render).mockResolvedValue({
      svg: '<svg data-testid="diagram"></svg>',
      diagramType: "flowchart-v2",
    });
    render(<LessonReader lesson={lesson("## Schéma\n\n```mermaid\nflowchart TD\n A-->B\n```")} />);
    expect(await screen.findByTestId("diagram")).toBeInTheDocument();
    expect(mermaid.initialize).toHaveBeenCalledWith(
      expect.objectContaining({ securityLevel: "strict" }),
    );
    expect(mermaid.render).toHaveBeenCalledWith(expect.any(String), "flowchart TD\n A-->B");
    expect(document.querySelector("pre")).toBeNull();
  });

  it("renders tables and code blocks", () => {
    render(<LessonReader lesson={LESSON} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText(/for i in range/)).toBeInTheDocument();
  });

  it("offers the PDF only when there is one", () => {
    const { unmount } = render(<LessonReader lesson={LESSON} />);
    expect(screen.getByRole("link", { name: "Télécharger le PDF" })).toHaveAttribute(
      "href",
      "/api/lessons/l1/pdf",
    );
    unmount();
    render(<LessonReader lesson={lesson("## A", { pdfUrl: null })} />);
    expect(screen.queryByRole("link", { name: "Télécharger le PDF" })).toBeNull();
  });

  it("shows the title, the word count, the reading time and a progress bar", () => {
    render(<LessonReader lesson={LESSON} />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Les boucles en Python" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/1\s840 mots/)).toBeInTheDocument();
    expect(screen.getByText(/environ 10 min de lecture/)).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "Progression de la lecture" }),
    ).toBeInTheDocument();
  });

  it("sets the reading column to 72 characters and the body to 18 px", () => {
    render(<LessonReader lesson={LESSON} />);
    const body = screen.getByTestId("lesson-body");
    expect(body.className).toContain("max-w-[72ch]");
    expect(body.className).toContain("text-[18px]");
  });
});
