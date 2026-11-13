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
  before: `Avant ${id}`,
  after: `Après ${id}`,
  reason: `Raison ${id}`,
  status: "proposed",
  blocks: [],
  author: "writer",
  facts: [],
  ...patch,
});

const MODS: ModificationView[] = [
  mod("m1"),
  mod("m2", { section: "summary" }),
  mod("m3", { status: "to_confirm", blocks: ["Chiffre absent"] }),
  mod("m4", { status: "to_confirm", blocks: ["Outil absent"], section: "skills" }),
  mod("m5", { status: "accepted" }),
];

function article(index: number): HTMLElement {
  const found = screen.getAllByRole("article")[index];
  if (!found) throw new Error(`Pas de carte ${index}`);
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
      "Résumé (1)",
      "Expériences (3)",
      "Compétences (1)",
    ]);
  });

  it("filters to what is left to decide and to what needs confirming", async () => {
    setup();
    expect(screen.getByRole("button", { name: "Toutes (5)" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await userEvent.click(screen.getByRole("button", { name: "À décider (4)" }));
    expect(screen.queryByText("Raison m5")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "À confirmer (2)" }));
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.getByText("Chiffre absent")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "À confirmer (2)" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("says when a filter is empty", async () => {
    setup([mod("m1")]);
    await userEvent.click(screen.getByRole("button", { name: "À confirmer (0)" }));
    expect(screen.getByText("Aucune modification dans ce filtre.")).toBeInTheDocument();
  });

  it("Accept all asks for acceptance and announces what is left to confirm one by one", async () => {
    const { onBulk } = setup();
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("2 modifications à confirmer une par une");
    await userEvent.click(screen.getByRole("button", { name: "Tout accepter" }));
    expect(onBulk).toHaveBeenCalledWith("accepted");
    expect(status).toHaveTextContent(
      "Modifications acceptées. 2 modifications à confirmer une par une.",
    );
  });

  it("uses the singular for a single modification to confirm", () => {
    setup([mod("m1"), mod("m3", { status: "to_confirm" })]);
    expect(screen.getByRole("status")).toHaveTextContent("1 modification à confirmer une par une");
  });

  it("disables Accept all when only to-confirm or decided modifications remain", () => {
    setup([mod("m3", { status: "to_confirm" }), mod("m5", { status: "accepted" })]);
    expect(screen.getByRole("button", { name: "Tout accepter" })).toBeDisabled();
  });

  it("passes the identifier of the modification with each decision", async () => {
    const { onDecide } = setup([mod("m1"), mod("m3", { status: "to_confirm" })]);
    const first = article(0);
    await userEvent.click(within(first).getByRole("button", { name: "Refuser" }));
    expect(onDecide).toHaveBeenCalledWith("m1", "refused");
    const second = article(1);
    await userEvent.click(within(second).getByRole("checkbox"));
    await userEvent.click(within(second).getByRole("button", { name: "Accepter" }));
    expect(onDecide).toHaveBeenLastCalledWith("m3", "accepted", { confirm: true });
  });

  it("locks everything while busy", () => {
    setup(MODS, true);
    expect(screen.getByRole("button", { name: "Tout accepter" })).toBeDisabled();
    for (const button of screen.getAllByRole("button", { name: "Refuser" })) {
      expect(button).toBeDisabled();
    }
  });

  it("says when there is nothing to review", () => {
    setup([]);
    expect(screen.getByText("Aucune modification proposée.")).toBeInTheDocument();
  });
});
