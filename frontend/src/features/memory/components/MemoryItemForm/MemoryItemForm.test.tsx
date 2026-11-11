import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryItemForm } from "./MemoryItemForm";

const base = {
  initial: null,
  chooseKind: false,
  disabled: false,
  onSubmit: vi.fn(),
  onCancel: vi.fn(),
};
const save = () => screen.getByRole("button", { name: "Enregistrer" });

describe("MemoryItemForm", () => {
  it("creates a new item with a chosen kind, level and parsed tags", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MemoryItemForm {...base} chooseKind onSubmit={onSubmit} />);
    await user.selectOptions(screen.getByLabelText("Type"), "Décision");
    await user.type(screen.getByLabelText("Titre"), "  Viser le NLP ");
    await user.type(screen.getByLabelText("Texte"), "Je me spécialise.");
    await user.type(screen.getByLabelText("Étiquettes"), "nlp, , carrière,nlp");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith({
      kind: "decision",
      title: "Viser le NLP",
      text: "Je me spécialise.",
      tags: ["nlp", "carrière"],
      level: null,
    });
  });

  it("offers a level for an acquis only", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MemoryItemForm {...base} chooseKind onSubmit={onSubmit} />);
    expect(screen.getByLabelText("Niveau")).toHaveValue("declare");
    await user.selectOptions(screen.getByLabelText("Niveau"), "En cours");
    await user.type(screen.getByLabelText("Titre"), "Attention");
    await user.type(screen.getByLabelText("Texte"), "Compris.");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "acquis", level: "en_cours" }),
    );
    await user.selectOptions(screen.getByLabelText("Type"), "Offre");
    expect(screen.queryByLabelText("Niveau")).not.toBeInTheDocument();
  });

  it("edits an existing item without a kind field", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    const initial = { title: "Attention", text: "Texte", tags: ["nlp"], level: "declare" as const };
    render(<MemoryItemForm {...base} initial={initial} onSubmit={onSubmit} />);
    expect(screen.queryByLabelText("Type")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Étiquettes")).toHaveValue("nlp");
    await user.clear(screen.getByLabelText("Titre"));
    await user.type(screen.getByLabelText("Titre"), "Attention v2");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith({ title: "Attention v2" });
  });

  it("sends only the changed fields when editing", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    const initial = { title: "Attention", text: "Texte", tags: ["nlp"], level: "declare" as const };
    render(<MemoryItemForm {...base} initial={initial} onSubmit={onSubmit} />);
    await user.type(screen.getByLabelText("Étiquettes"), ", cours");
    await user.selectOptions(screen.getByLabelText("Niveau"), "En cours");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith({ tags: ["nlp", "cours"], level: "en_cours" });
  });

  it("offers no text field for a document and never sends its text", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    const initial = { title: "Cours", text: "x".repeat(25_000), tags: [], level: null };
    render(<MemoryItemForm {...base} initial={initial} withText={false} onSubmit={onSubmit} />);
    expect(screen.queryByLabelText("Texte")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Titre"), " v2");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith({ title: "Cours v2" });
  });

  it("hides the level when the item has none to edit", () => {
    const initial = { title: "Cours", text: "Texte", tags: [], level: null };
    render(<MemoryItemForm {...base} initial={initial} />);
    expect(screen.queryByLabelText("Niveau")).not.toBeInTheDocument();
  });

  it("refuses an empty title or text", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MemoryItemForm {...base} chooseKind onSubmit={onSubmit} />);
    expect(save()).toBeDisabled();
    await user.type(screen.getByLabelText("Titre"), "   ");
    await user.type(screen.getByLabelText("Texte"), "Un texte");
    expect(save()).toBeDisabled();
    await user.keyboard("{Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables every field while busy", () => {
    render(<MemoryItemForm {...base} chooseKind disabled />);
    expect(screen.getByLabelText("Titre")).toBeDisabled();
    expect(screen.getByLabelText("Texte")).toBeDisabled();
    expect(save()).toBeDisabled();
  });

  it("cancels", async () => {
    const onCancel = vi.fn();
    render(<MemoryItemForm {...base} onCancel={onCancel} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Annuler" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
