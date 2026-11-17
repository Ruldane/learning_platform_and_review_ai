import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ChangeView } from "../viewTypes";
import { ChangeList } from "./ChangeList";

const change = (over: Partial<ChangeView> = {}): ChangeView => ({
  callId: "call1",
  at: "2026-11-17T09:00:00Z",
  action: "skills_add_proof",
  rows: 2,
  tables: ["skill_proofs"],
  undoneAt: null,
  ...over,
});

describe("ChangeList", () => {
  it("undo button appears only for undoable calls", async () => {
    const onUndo = vi.fn();
    render(
      <ChangeList
        changes={[
          change(),
          change({ callId: "call2", action: "cv_edit", rows: 1, undoneAt: "2026-11-17T10:00:00Z" }),
        ]}
        busyIds={[]}
        onUndo={onUndo}
      />,
    );
    const buttons = screen.getAllByRole("button", { name: "Annuler" });
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveAccessibleDescription("skills_add_proof");
    expect(screen.getByText(/Annulé le/)).toBeInTheDocument();
    expect(screen.getByText(/2 lignes dans skill_proofs/)).toBeInTheDocument();
    expect(screen.getByText(/1 ligne dans/)).toBeInTheDocument();
    await userEvent.click(buttons[0]!);
    expect(onUndo).toHaveBeenCalledWith("call1");
  });

  it("disables the button of a change being undone", () => {
    render(<ChangeList changes={[change()]} busyIds={["call1"]} onUndo={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Annuler" })).toBeDisabled();
  });

  it("says when Claude changed nothing", () => {
    render(<ChangeList changes={[]} busyIds={[]} onUndo={vi.fn()} />);
    expect(screen.getByText("Aucun changement fait par Claude.")).toBeInTheDocument();
  });
});
