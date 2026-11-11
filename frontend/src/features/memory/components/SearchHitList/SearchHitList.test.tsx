import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { hit } from "../viewFixtures";
import { SearchHitList } from "./SearchHitList";

describe("SearchHitList", () => {
  it("shows kind, title, author, excerpt and the score", () => {
    render(<SearchHitList hits={[hit()]} onOpen={vi.fn()} />);
    expect(screen.getByText("Document")).toBeInTheDocument();
    expect(screen.getByText("Cours NLP")).toBeInTheDocument();
    expect(screen.getByText("Archiviste")).toBeInTheDocument();
    expect(screen.getByText("L'attention relie chaque jeton aux autres.")).toBeInTheDocument();
    expect(screen.getByText("0,83")).toBeInTheDocument();
  });

  it("opens the item of a hit", async () => {
    const onOpen = vi.fn();
    render(<SearchHitList hits={[hit({ item_id: "doc-9" })]} onOpen={onOpen} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Cours NLP" }));
    expect(onOpen).toHaveBeenCalledWith("doc-9");
  });

  it("shows a plain title when there is nothing to open", () => {
    render(<SearchHitList hits={[hit()]} />);
    expect(screen.getByText("Cours NLP")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("keeps two fragments of the same item apart", () => {
    render(
      <SearchHitList
        hits={[hit({ chunk_id: "c1" }), hit({ chunk_id: "c2", score: 0.5 })]}
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("shows a message when there is no hit", () => {
    render(<SearchHitList hits={[]} onOpen={vi.fn()} />);
    expect(screen.getByText("Aucun résultat")).toBeInTheDocument();
  });
});
