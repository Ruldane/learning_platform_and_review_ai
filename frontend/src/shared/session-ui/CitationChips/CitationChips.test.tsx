import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CitationChips } from "./CitationChips";

describe("CitationChips", () => {
  it("opens a web source in a new tab without leaking the opener", () => {
    render(
      <CitationChips
        citations={[{ index: 1, title: "Doc", url: "https://a.org/x", memory_item_id: null }]}
      />,
    );
    const link = screen.getByRole("link", { name: "Source 1 : Doc" });
    expect(link).toHaveTextContent("1");
    expect(link).toHaveAttribute("href", "https://a.org/x");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("links a memory item to the memory page", () => {
    render(
      <CitationChips
        citations={[{ index: 2, title: "Ma note", url: null, memory_item_id: "it 1" }]}
      />,
    );
    const link = screen.getByRole("link", { name: "Source 2 : Ma note" });
    expect(link).toHaveAttribute("href", "/memoire?item=it%201");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("never makes a link from a script address", () => {
    render(
      <CitationChips
        citations={[{ index: 3, title: "Piège", url: "javascript:alert(1)", memory_item_id: null }]}
      />,
    );
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("3")).toHaveAccessibleName("Source 3 : Piège");
  });

  it("names a source without title and renders nothing when there is none", () => {
    const { container, rerender } = render(
      <CitationChips
        citations={[{ index: 1, title: " ", url: "https://a.org", memory_item_id: null }]}
      />,
    );
    expect(screen.getByRole("link", { name: "Source 1 : sans titre" })).toBeInTheDocument();
    rerender(<CitationChips citations={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("lists the chips in index order", () => {
    render(
      <CitationChips
        citations={[
          { index: 2, title: "B", url: "https://b.org", memory_item_id: null },
          { index: 1, title: "A", url: "https://a.org", memory_item_id: null },
        ]}
      />,
    );
    expect(screen.getAllByRole("link").map((l) => l.textContent)).toEqual(["1", "2"]);
  });
});
