import { render, screen } from "@testing-library/react";
import mermaid from "mermaid";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MermaidSvg } from "./MermaidSvg";

vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

describe("MermaidSvg", () => {
  beforeEach(() => {
    vi.mocked(mermaid.initialize).mockClear();
    vi.mocked(mermaid.render).mockReset();
  });

  it("renders the diagram with the strict security level", async () => {
    vi.mocked(mermaid.render).mockResolvedValue({
      svg: '<svg data-testid="diagram"></svg>',
      diagramType: "flowchart-v2",
    });
    render(<MermaidSvg code={"flowchart TD\n A-->B"} title="Carte du domaine" />);
    expect(await screen.findByTestId("diagram")).toBeInTheDocument();
    expect(mermaid.initialize).toHaveBeenCalledWith(
      expect.objectContaining({ startOnLoad: false, securityLevel: "strict" }),
    );
    expect(mermaid.render).toHaveBeenCalledWith(
      expect.stringMatching(/^mermaid-/),
      "flowchart TD\n A-->B",
    );
    expect(screen.getByRole("img", { name: "Schéma : Carte du domaine" })).toBeInTheDocument();
  });

  it("shows the code in a pre block when rendering fails", async () => {
    vi.mocked(mermaid.render).mockRejectedValue(new Error("Parse error"));
    render(<MermaidSvg code={"flowchart TD\n A-->"} title="Frise" />);
    const alert = await screen.findByRole("alert");
    const code = alert.nextElementSibling;
    expect(code?.tagName).toBe("PRE");
    expect(code?.textContent).toBe("flowchart TD\n A-->");
    expect(screen.getByRole("alert")).toHaveTextContent("n'a pas pu être dessiné");
  });
});
