import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NO_FILTERS, row } from "../viewFixtures";
import { MemoryTable } from "./MemoryTable";

const base = {
  items: [],
  total: 0,
  offset: 0,
  limit: 25,
  filters: NO_FILTERS,
  authors: [],
  selected: [],
  onFiltersChange: vi.fn(),
  onSelect: vi.fn(),
  onOpen: vi.fn(),
  onMerge: vi.fn(),
  onPage: vi.fn(),
  merging: false,
};

const two = [row({ id: "a", title: "Premier" }), row({ id: "b", title: "Second" })];
const mergeButton = () => screen.getByRole("button", { name: "Fusionner" });

describe("MemoryTable", () => {
  it("shows kind, author and level", () => {
    render(
      <MemoryTable
        {...base}
        total={1}
        items={[row({ kind: "acquis", created_by: "archivist", level: "declare" })]}
      />,
    );
    const table = within(screen.getByRole("table"));
    expect(table.getByText("Acquis")).toBeInTheDocument();
    expect(table.getByText("Archiviste")).toBeInTheDocument();
    expect(table.getByText("Déclaré")).toBeInTheDocument();
  });

  it("shows the empty state", () => {
    render(<MemoryTable {...base} />);
    expect(screen.getByText("Aucun élément en mémoire")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("flags items that are not indexed yet and pending ones", () => {
    render(
      <MemoryTable
        {...base}
        total={2}
        items={[row({ indexed: false }), row({ id: "b", status: "pending", kind: "decision" })]}
      />,
    );
    expect(screen.getByText("Pas encore indexé")).toBeInTheDocument();
    expect(screen.getByText("À confirmer")).toBeInTheDocument();
  });

  it("opens an item from its title", async () => {
    const onOpen = vi.fn();
    render(<MemoryTable {...base} total={2} items={two} onOpen={onOpen} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Second" }));
    expect(onOpen).toHaveBeenCalledWith("b");
  });

  it("selects and unselects items", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <MemoryTable {...base} total={2} items={two} onSelect={onSelect} />,
    );
    await user.click(screen.getByRole("checkbox", { name: "Sélectionner « Premier »" }));
    expect(onSelect).toHaveBeenLastCalledWith(["a"]);
    rerender(<MemoryTable {...base} total={2} items={two} onSelect={onSelect} selected={["a"]} />);
    await user.click(screen.getByRole("checkbox", { name: "Sélectionner « Premier »" }));
    expect(onSelect).toHaveBeenLastCalledWith([]);
  });

  it("merge needs two items of the same non-document kind", async () => {
    const onMerge = vi.fn();
    const user = userEvent.setup();
    render(<MemoryTable {...base} total={2} items={two} selected={["a", "b"]} onMerge={onMerge} />);
    await user.click(mergeButton());
    await user.click(screen.getByRole("button", { name: "Oui, fusionner" }));
    expect(onMerge).toHaveBeenCalledWith("a", ["b"]);
  });

  it("merges into the first checked item", async () => {
    const onMerge = vi.fn();
    const user = userEvent.setup();
    render(<MemoryTable {...base} total={2} items={two} selected={["b", "a"]} onMerge={onMerge} />);
    await user.click(mergeButton());
    await user.click(screen.getByRole("button", { name: "Oui, fusionner" }));
    expect(onMerge).toHaveBeenCalledWith("b", ["a"]);
  });

  it("asks for an in-page confirmation before merging, and lets the user back out", async () => {
    const onMerge = vi.fn();
    const user = userEvent.setup();
    render(<MemoryTable {...base} total={2} items={two} selected={["a", "b"]} onMerge={onMerge} />);
    await user.click(mergeButton());
    expect(screen.getByText(/Fondre 2 éléments dans « Premier »/)).toBeInTheDocument();
    expect(onMerge).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Non, annuler" }));
    expect(onMerge).not.toHaveBeenCalled();
    expect(mergeButton()).toBeEnabled();
  });

  it("locks the merge and the selection while the merge is in flight", () => {
    render(<MemoryTable {...base} total={2} items={two} selected={["a", "b"]} merging />);
    expect(mergeButton()).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: "Sélectionner « Premier »" })).toBeDisabled();
  });

  it("disables merge for one item, mixed kinds or documents", () => {
    const mixed = [row({ id: "a" }), row({ id: "b", kind: "lecon" })];
    const docs = [row({ id: "a", kind: "document" }), row({ id: "b", kind: "document" })];
    const { rerender } = render(<MemoryTable {...base} total={2} items={two} selected={["a"]} />);
    expect(mergeButton()).toBeDisabled();
    rerender(<MemoryTable {...base} total={2} items={mixed} selected={["a", "b"]} />);
    expect(mergeButton()).toBeDisabled();
    rerender(<MemoryTable {...base} total={2} items={docs} selected={["a", "b"]} />);
    expect(mergeButton()).toBeDisabled();
  });

  it("disables merge when a selected item is not on the page", () => {
    render(<MemoryTable {...base} total={3} items={two} selected={["a", "ailleurs"]} />);
    expect(mergeButton()).toBeDisabled();
  });

  it("pages with the offset and the limit", async () => {
    const onPage = vi.fn();
    const user = userEvent.setup();
    render(<MemoryTable {...base} total={60} offset={25} limit={25} items={two} onPage={onPage} />);
    expect(screen.getByText("26–27 sur 60")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Suivant" }));
    expect(onPage).toHaveBeenLastCalledWith(50);
    await user.click(screen.getByRole("button", { name: "Précédent" }));
    expect(onPage).toHaveBeenLastCalledWith(0);
  });

  it("still shows the pager when the page is empty but there are more pages", async () => {
    const onPage = vi.fn();
    render(<MemoryTable {...base} total={30} offset={50} limit={25} items={[]} onPage={onPage} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Précédent" }));
    expect(onPage).toHaveBeenCalledWith(25);
  });

  it("disables the paging buttons at both ends", () => {
    render(<MemoryTable {...base} total={2} offset={0} limit={25} items={two} />);
    expect(screen.getByRole("button", { name: "Précédent" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Suivant" })).toBeDisabled();
  });

  it("keeps the filters visible and forwards their changes", async () => {
    const onFiltersChange = vi.fn();
    render(<MemoryTable {...base} onFiltersChange={onFiltersChange} />);
    await userEvent.setup().type(screen.getByLabelText("Étiquette"), "x");
    expect(onFiltersChange).toHaveBeenCalledWith({ ...NO_FILTERS, tag: "x" });
  });
});
