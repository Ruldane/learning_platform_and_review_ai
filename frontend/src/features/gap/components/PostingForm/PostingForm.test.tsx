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

const SUBMIT = "Analyze posting";

describe("PostingForm", () => {
  it("sends the link", async () => {
    const { onSubmit } = setup();
    await userEvent.type(screen.getByLabelText("Posting link"), " https://example.org/offre ");
    await userEvent.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith({ url: "https://example.org/offre" });
  });

  it("sends the pasted text from the Text tab", async () => {
    const { onSubmit } = setup();
    await userEvent.click(screen.getByRole("tab", { name: "Text" }));
    await userEvent.type(screen.getByLabelText("Posting text"), "Développeuse front");
    await userEvent.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith({ text: "Développeuse front" });
  });

  it("is disabled while empty", () => {
    setup();
    expect(screen.getByRole("button", { name: SUBMIT })).toBeDisabled();
  });

  it("switches to the Text tab with the message on posting_unreadable", () => {
    const { rerender } = setup();
    expect(screen.getByRole("tab", { name: "Link" })).toHaveAttribute("aria-selected", "true");
    rerender({
      error: {
        code: "posting_unreadable",
        message: "This posting could not be read from its link. Paste the posting text instead.",
      },
    });
    expect(screen.getByRole("tab", { name: "Text" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("Posting text")).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("Paste the posting text instead.");
  });

  it("keeps the Link tab on another error", () => {
    setup({ error: { code: "internal", message: "Something went wrong." } });
    expect(screen.getByRole("tab", { name: "Link" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong.");
  });

  it("sends once on a double click", async () => {
    const { onSubmit } = setup();
    await userEvent.type(screen.getByLabelText("Posting link"), "https://example.org/a");
    await userEvent.dblClick(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("can send again once the answer came back", async () => {
    const { onSubmit, rerender } = setup();
    await userEvent.type(screen.getByLabelText("Posting link"), "https://example.org/a");
    await userEvent.click(screen.getByRole("button", { name: SUBMIT }));
    rerender({ pending: true });
    rerender({ pending: false, error: { code: "internal", message: "Something went wrong." } });
    await userEvent.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledTimes(2);
  });

  it("locks the form while pending", () => {
    setup({ pending: true });
    expect(screen.getByRole("button", { name: "Analyzing…" })).toBeDisabled();
    expect(screen.getByLabelText("Posting link")).toBeDisabled();
  });

  it("moves between tabs with the arrow keys", async () => {
    setup();
    screen.getByRole("tab", { name: "Link" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Text" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Text" })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Link" })).toHaveFocus();
  });

  it("links each tab to its panel", () => {
    setup();
    const tab = screen.getByRole("tab", { name: "Link" });
    const panel = document.getElementById(tab.getAttribute("aria-controls") ?? "");
    expect(panel).toHaveAttribute("role", "tabpanel");
    expect(panel).toHaveAttribute("aria-labelledby", tab.id);
  });
});
