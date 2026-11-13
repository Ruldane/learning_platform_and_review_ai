import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FormErrorView } from "../viewTypes";
import { PostingForm } from "./PostingForm";

interface Props {
  pending?: boolean;
  error?: FormErrorView | null;
}

function setup(props: Props = {}) {
  const onSubmit = vi.fn();
  const ui = (next: Props) => (
    <PostingForm pending={next.pending ?? false} error={next.error ?? null} onSubmit={onSubmit} />
  );
  const view = render(ui(props));
  return { onSubmit, rerender: (next: Props) => view.rerender(ui(next)) };
}

const SUBMIT = "Analyser l'offre";

describe("PostingForm", () => {
  it("sends the link", async () => {
    const { onSubmit } = setup();
    await userEvent.type(screen.getByLabelText("Lien de l'offre"), " https://example.org/offre ");
    await userEvent.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith({ url: "https://example.org/offre" });
  });

  it("sends the pasted text from the Texte tab", async () => {
    const { onSubmit } = setup();
    await userEvent.click(screen.getByRole("tab", { name: "Texte" }));
    await userEvent.type(screen.getByLabelText("Texte de l'offre"), "Développeuse front");
    await userEvent.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith({ text: "Développeuse front" });
  });

  it("is disabled while empty", () => {
    setup();
    expect(screen.getByRole("button", { name: SUBMIT })).toBeDisabled();
  });

  it("switches to the Texte tab with the message on posting_unreadable", () => {
    const { rerender } = setup();
    expect(screen.getByRole("tab", { name: "Lien" })).toHaveAttribute("aria-selected", "true");
    rerender({
      error: {
        code: "posting_unreadable",
        message: "Impossible de lire cette offre : colle son texte.",
      },
    });
    expect(screen.getByRole("tab", { name: "Texte" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("Texte de l'offre")).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("Impossible de lire cette offre");
  });

  it("keeps the Lien tab on another error", () => {
    setup({ error: { code: "internal", message: "Oups." } });
    expect(screen.getByRole("tab", { name: "Lien" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Oups.");
  });

  it("sends once on a double click", async () => {
    const { onSubmit } = setup();
    await userEvent.type(screen.getByLabelText("Lien de l'offre"), "https://example.org/a");
    await userEvent.dblClick(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("can send again once the answer came back", async () => {
    const { onSubmit, rerender } = setup();
    await userEvent.type(screen.getByLabelText("Lien de l'offre"), "https://example.org/a");
    await userEvent.click(screen.getByRole("button", { name: SUBMIT }));
    rerender({ pending: true });
    rerender({ pending: false, error: { code: "internal", message: "Oups." } });
    await userEvent.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledTimes(2);
  });

  it("locks the form while pending", () => {
    setup({ pending: true });
    expect(screen.getByRole("button", { name: "Analyse en cours…" })).toBeDisabled();
    expect(screen.getByLabelText("Lien de l'offre")).toBeDisabled();
  });

  it("moves between tabs with the arrow keys", async () => {
    setup();
    screen.getByRole("tab", { name: "Lien" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Texte" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Texte" })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Lien" })).toHaveFocus();
  });

  it("links each tab to its panel", () => {
    setup();
    const tab = screen.getByRole("tab", { name: "Lien" });
    const panel = document.getElementById(tab.getAttribute("aria-controls") ?? "");
    expect(panel).toHaveAttribute("role", "tabpanel");
    expect(panel).toHaveAttribute("aria-labelledby", tab.id);
  });
});
