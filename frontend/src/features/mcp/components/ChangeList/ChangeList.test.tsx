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
    const buttons = screen.getAllByRole("button", { name: "Undo" });
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveAccessibleDescription("skills_add_proof");
    expect(screen.getByText(/Undone on/)).toBeInTheDocument();
    expect(screen.getByText(/2 rows in skill_proofs/)).toBeInTheDocument();
    expect(screen.getByText(/1 row in/)).toBeInTheDocument();
    await userEvent.click(buttons[0]!);
    expect(onUndo).toHaveBeenCalledWith("call1");
  });

  it("disables the button of a change being undone", () => {
    render(<ChangeList changes={[change()]} busyIds={["call1"]} onUndo={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Undo" })).toBeDisabled();
  });

  it("says when Claude changed nothing", () => {
    render(<ChangeList changes={[]} busyIds={[]} onUndo={vi.fn()} />);
    expect(screen.getByText("No changes made by Claude.")).toBeInTheDocument();
  });
});
