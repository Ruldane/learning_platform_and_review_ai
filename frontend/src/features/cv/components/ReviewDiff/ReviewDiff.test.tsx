import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ModificationView } from "../viewTypes";
import { ReviewDiff } from "./ReviewDiff";

const mod = (id: string, patch: Partial<ModificationView> = {}): ModificationView => ({
  id,
  ref: id,
  section: "experience",
  action: "rewrite",
  type: "clarity",
  before: `Before ${id}`,
  after: `After ${id}`,
  reason: `Reason ${id}`,
  status: "proposed",
  blocks: [],
  author: "writer",
  facts: [],
  ...patch,
});

const MODS: ModificationView[] = [
  mod("m1"),
  mod("m2", { section: "summary" }),
  mod("m3", { status: "to_confirm", blocks: ["Unsupported number"] }),
  mod("m4", { status: "to_confirm", blocks: ["Unsupported tool"], section: "skills" }),
  mod("m5", { status: "accepted" }),
];

function article(index: number): HTMLElement {
  const found = screen.getAllByRole("article")[index];
  if (!found) throw new Error(`Missing card ${index}`);
  return found;
}

function setup(mods = MODS, busy = false) {
  const onDecide = vi.fn();
  const onBulk = vi.fn();
  render(<ReviewDiff mods={mods} onDecide={onDecide} onBulk={onBulk} busy={busy} />);
  return { onDecide, onBulk };
}

describe("ReviewDiff", () => {
  it("groups the modifications by section, in the order of a CV", () => {
    setup();
    const headings = screen
      .getAllByRole("heading", { level: 3 })
      .filter((h) => /\(\d\)$/.test(h.textContent ?? ""));
    expect(headings.map((h) => h.textContent)).toEqual([
      "Summary (1)",
      "Experience (3)",
      "Skills (1)",
    ]);
  });

  it("filters to what is left to decide and to what needs confirming", async () => {
    setup();
    expect(screen.getByRole("button", { name: "All (5)" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(screen.getByRole("button", { name: "To decide (4)" }));
    expect(screen.queryByText("Reason m5")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "To confirm (2)" }));
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.getByText("Unsupported number")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "To confirm (2)" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("says when a filter is empty", async () => {
    setup([mod("m1")]);
    await userEvent.click(screen.getByRole("button", { name: "To confirm (0)" }));
    expect(screen.getByText("No changes in this filter.")).toBeInTheDocument();
  });

  it("Accept all asks for acceptance and announces what is left to confirm one by one", async () => {
    const { onBulk } = setup();
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("2 changes to confirm individually");
    await userEvent.click(screen.getByRole("button", { name: "Accept all" }));
    expect(onBulk).toHaveBeenCalledWith("accepted");
    expect(status).toHaveTextContent(
      "Changes accepted. 2 changes to confirm individually.",
    );
  });

  it("uses the singular for a single modification to confirm", () => {
    setup([mod("m1"), mod("m3", { status: "to_confirm" })]);
    expect(screen.getByRole("status")).toHaveTextContent("1 change to confirm individually");
  });

  it("disables Accept all when only to-confirm or decided modifications remain", () => {
    setup([mod("m3", { status: "to_confirm" }), mod("m5", { status: "accepted" })]);
    expect(screen.getByRole("button", { name: "Accept all" })).toBeDisabled();
  });

  it("passes the identifier of the modification with each decision", async () => {
    const { onDecide } = setup([mod("m1"), mod("m3", { status: "to_confirm" })]);
    const first = article(0);
    await userEvent.click(within(first).getByRole("button", { name: "Refuse" }));
    expect(onDecide).toHaveBeenCalledWith("m1", "refused");
    const second = article(1);
    await userEvent.click(within(second).getByRole("checkbox"));
    await userEvent.click(within(second).getByRole("button", { name: "Accept" }));
    expect(onDecide).toHaveBeenLastCalledWith("m3", "accepted", { confirm: true });
  });

  it("locks everything while busy", () => {
    setup(MODS, true);
    expect(screen.getByRole("button", { name: "Accept all" })).toBeDisabled();
    for (const button of screen.getAllByRole("button", { name: "Refuse" })) {
      expect(button).toBeDisabled();
    }
  });

  it("says when there is nothing to review", () => {
    setup([]);
    expect(screen.getByText("No suggested changes.")).toBeInTheDocument();
  });
});
