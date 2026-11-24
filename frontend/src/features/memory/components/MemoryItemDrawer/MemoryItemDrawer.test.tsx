import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { detail } from "../viewFixtures";
import { MemoryItemDrawer } from "./MemoryItemDrawer";

const base = {
  open: true,
  item: detail({ id: "a", title: "Attention" }),
  busy: false,
  error: null,
  onClose: vi.fn(),
  onSave: vi.fn(),
  onDelete: vi.fn(),
  onOpenItem: vi.fn(),
};

describe("MemoryItemDrawer", () => {
  it("is a non-blocking dialog focused on its title", () => {
    render(<MemoryItemDrawer {...base} />);
    const dialog = screen.getByRole("dialog", { name: "Attention" });
    expect(dialog).not.toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("heading", { name: "Attention" })).toHaveFocus();
  });

  it("renders nothing when closed", () => {
    render(<MemoryItemDrawer {...base} open={false} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes with Escape and with its button", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<MemoryItemDrawer {...base} onClose={onClose} />);
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("lists the journal with author and reason", () => {
    const writes = [
      {
        id: "w1",
        action: "create" as const,
        author: "archivist",
        session_id: null,
        reason: "Document « Cours NLP » marqué « déjà appris ».",
        created_at: "2026-11-11T10:00:00Z",
      },
    ];
    render(<MemoryItemDrawer {...base} item={detail({ writes })} />);
    const journal = within(screen.getByRole("region", { name: "Write log" }));
    expect(journal.getByText("Document « Cours NLP » marqué « déjà appris ».")).toBeInTheDocument();
    expect(journal.getByText("Creation")).toBeInTheDocument();
    expect(journal.getByText("Archivist")).toBeInTheDocument();
  });

  it("shows the text, the tags, the evidence and the chunks", () => {
    const item = detail({
      tags: ["nlp"],
      evidence: ["https://exemple.test/preuve"],
      level: "validated",
      indexed: false,
      chunks: [{ id: "c1", ordinal: 0, text: "Premier fragment", token_count: 42 }],
    });
    render(<MemoryItemDrawer {...base} item={item} />);
    expect(screen.getByText("Le mécanisme d'attention pondère les jetons.")).toBeInTheDocument();
    expect(screen.getByText("nlp")).toBeInTheDocument();
    expect(screen.getByText("https://exemple.test/preuve")).toBeInTheDocument();
    expect(screen.getByText("Validated")).toBeInTheDocument();
    expect(screen.getByText("Not indexed yet")).toBeInTheDocument();
    expect(screen.getByText("Premier fragment")).toBeInTheDocument();
    expect(screen.getByText("Chunk 1 · 42 tokens")).toBeInTheDocument();
  });

  it("asks inline before deleting", async () => {
    const onDelete = vi.fn();
    const user = userEvent.setup();
    render(<MemoryItemDrawer {...base} onDelete={onDelete} />);
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(screen.getByText("Delete permanently?")).toBeInTheDocument();
    expect(onDelete).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "No, keep" }));
    expect(screen.queryByText("Delete permanently?")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Yes, delete" }));
    expect(onDelete).toHaveBeenCalledWith("a");
  });

  it("opens a neighbor", async () => {
    const onOpenItem = vi.fn();
    const neighbors = [
      { item_id: "n1", title: "Transformeurs", kind: "lesson" as const, score: 0.71 },
    ];
    render(<MemoryItemDrawer {...base} item={detail({ neighbors })} onOpenItem={onOpenItem} />);
    expect(screen.getByText("0.71")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: /Transformeurs/ }));
    expect(onOpenItem).toHaveBeenCalledWith("n1");
  });

  it("opens an Obsidian note linked by the synchronized document", async () => {
    const onOpenItem = vi.fn();
    const linkedNotes = [{ itemId: "note-obsidian", title: "Notions du dossier" }];
    render(<MemoryItemDrawer {...base} item={detail({ linkedNotes })} onOpenItem={onOpenItem} />);
    expect(screen.getByRole("heading", { name: "Linked notes" })).toBeVisible();
    await userEvent.setup().click(screen.getByRole("button", { name: "Notions du dossier" }));
    expect(onOpenItem).toHaveBeenCalledWith("note-obsidian");
  });

  it("edits the item and saves an ItemEdit", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(
      <MemoryItemDrawer
        {...base}
        item={detail({ tags: ["nlp"], level: "declared" })}
        onSave={onSave}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Attention v2");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith({ title: "Attention v2" });
  });

  it("edits only the title and tags of a document", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(
      <MemoryItemDrawer
        {...base}
        item={detail({ kind: "document", level: null, tags: ["nlp"], text: "x".repeat(25_000) })}
        onSave={onSave}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.queryByLabelText("Text")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Tags"), ", cours");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith({ tags: ["nlp", "cours"] });
  });

  it("does not offer the level of a validated acquis", async () => {
    render(<MemoryItemDrawer {...base} item={detail({ level: "proven" })} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.queryByLabelText("Level")).not.toBeInTheDocument();
  });

  it("creates an item when there is none", async () => {
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<MemoryItemDrawer {...base} item={null} onSave={onSave} />);
    expect(screen.getByRole("dialog", { name: "New item" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Type"), "Posting");
    await user.type(screen.getByLabelText("Title"), "Stage NLP");
    await user.type(screen.getByLabelText("Text"), "Offre vue en ligne.");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "posting", title: "Stage NLP" }),
    );
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("shows an error and locks the actions while busy", () => {
    render(<MemoryItemDrawer {...base} busy error="Suppression impossible." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Suppression impossible.");
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Edit" })).toBeDisabled();
  });

  it("refocuses the title when another item is opened", () => {
    const { rerender } = render(<MemoryItemDrawer {...base} />);
    rerender(<MemoryItemDrawer {...base} item={detail({ id: "n1", title: "Voisin" })} />);
    expect(screen.getByRole("heading", { name: "Voisin" })).toHaveFocus();
  });
});
