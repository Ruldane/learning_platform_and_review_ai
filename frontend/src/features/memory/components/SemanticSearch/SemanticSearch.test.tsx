import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { hit } from "../viewFixtures";
import { SemanticSearch } from "./SemanticSearch";

const base = { hits: null, pending: false, onSearch: vi.fn(), onOpen: vi.fn() };

describe("SemanticSearch", () => {
  it("shows scores", () => {
    render(<SemanticSearch {...base} hits={[hit()]} />);
    expect(screen.getByText("0,83")).toBeInTheDocument();
  });

  it("searches with the trimmed query and the checked kinds", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<SemanticSearch {...base} onSearch={onSearch} />);
    await user.type(screen.getByLabelText("Requête"), "  attention ");
    await user.click(screen.getByRole("checkbox", { name: "Leçon" }));
    await user.click(screen.getByRole("button", { name: "Rechercher" }));
    expect(onSearch).toHaveBeenCalledWith("attention", ["lecon"]);
  });

  it("searches on Enter and with no kind checked by default", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<SemanticSearch {...base} onSearch={onSearch} />);
    await user.type(screen.getByLabelText("Requête"), "rust{Enter}");
    expect(onSearch).toHaveBeenCalledWith("rust", []);
  });

  it("does not search an empty query", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<SemanticSearch {...base} onSearch={onSearch} />);
    await user.type(screen.getByLabelText("Requête"), "   {Enter}");
    expect(screen.getByRole("button", { name: "Rechercher" })).toBeDisabled();
    expect(onSearch).not.toHaveBeenCalled();
  });

  it("shows nothing before the first search and a message for no hit", () => {
    const { rerender } = render(<SemanticSearch {...base} />);
    expect(screen.queryByText("Aucun résultat")).not.toBeInTheDocument();
    rerender(<SemanticSearch {...base} hits={[]} />);
    expect(screen.getByText("Aucun résultat")).toBeInTheDocument();
  });

  it("shows the pending state and locks the button", () => {
    render(<SemanticSearch {...base} pending />);
    expect(screen.getByRole("button", { name: "Recherche…" })).toBeDisabled();
  });

  it("opens the item of a hit", async () => {
    const onOpen = vi.fn();
    render(<SemanticSearch {...base} hits={[hit({ item_id: "x" })]} onOpen={onOpen} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Cours NLP" }));
    expect(onOpen).toHaveBeenCalledWith("x");
  });
});
