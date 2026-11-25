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
const save = () => screen.getByRole("button", { name: "Save" });

describe("MemoryItemForm", () => {
  it("creates a new item with a chosen kind, level and parsed tags", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MemoryItemForm {...base} chooseKind onSubmit={onSubmit} />);
    await user.selectOptions(screen.getByLabelText("Type"), "Decision");
    await user.type(screen.getByLabelText("Title"), "  Viser le NLP ");
    await user.type(screen.getByLabelText("Text"), "Je me spécialise.");
    await user.type(screen.getByLabelText("Tags"), "nlp, , carrière,nlp");
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
    expect(screen.getByLabelText("Level")).toHaveValue("declared");
    await user.selectOptions(screen.getByLabelText("Level"), "In progress");
    await user.type(screen.getByLabelText("Title"), "Attention");
    await user.type(screen.getByLabelText("Text"), "Compris.");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "skill", level: "in_progress" }),
    );
    await user.selectOptions(screen.getByLabelText("Type"), "Posting");
    expect(screen.queryByLabelText("Level")).not.toBeInTheDocument();
  });

  it("edits an existing item without a kind field", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    const initial = {
      title: "Attention",
      text: "Text",
      tags: ["nlp"],
      level: "declared" as const,
    };
    render(<MemoryItemForm {...base} initial={initial} onSubmit={onSubmit} />);
    expect(screen.queryByLabelText("Type")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Tags")).toHaveValue("nlp");
    await user.clear(screen.getByLabelText("Title"));
    await user.type(screen.getByLabelText("Title"), "Attention v2");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith({ title: "Attention v2" });
  });

  it("sends only the changed fields when editing", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    const initial = {
      title: "Attention",
      text: "Text",
      tags: ["nlp"],
      level: "declared" as const,
    };
    render(<MemoryItemForm {...base} initial={initial} onSubmit={onSubmit} />);
    await user.type(screen.getByLabelText("Tags"), ", cours");
    await user.selectOptions(screen.getByLabelText("Level"), "In progress");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith({ tags: ["nlp", "cours"], level: "in_progress" });
  });

  it("offers no text field for a document and never sends its text", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    const initial = { title: "Cours", text: "x".repeat(25_000), tags: [], level: null };
    render(<MemoryItemForm {...base} initial={initial} withText={false} onSubmit={onSubmit} />);
    expect(screen.queryByLabelText("Text")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Title"), " v2");
    await user.click(save());
    expect(onSubmit).toHaveBeenCalledWith({ title: "Cours v2" });
  });

  it("hides the level when the item has none to edit", () => {
    const initial = { title: "Cours", text: "Text", tags: [], level: null };
    render(<MemoryItemForm {...base} initial={initial} />);
    expect(screen.queryByLabelText("Level")).not.toBeInTheDocument();
  });

  it("refuses an empty title or text", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MemoryItemForm {...base} chooseKind onSubmit={onSubmit} />);
    expect(save()).toBeDisabled();
    await user.type(screen.getByLabelText("Title"), "   ");
    await user.type(screen.getByLabelText("Text"), "Un texte");
    expect(save()).toBeDisabled();
    await user.keyboard("{Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables every field while busy", () => {
    render(<MemoryItemForm {...base} chooseKind disabled />);
    expect(screen.getByLabelText("Title")).toBeDisabled();
    expect(screen.getByLabelText("Text")).toBeDisabled();
    expect(save()).toBeDisabled();
  });

  it("cancels", async () => {
    const onCancel = vi.fn();
    render(<MemoryItemForm {...base} onCancel={onCancel} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
