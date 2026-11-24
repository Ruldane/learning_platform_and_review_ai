import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { NoteView } from "../viewTypes";
import { ProposalCard } from "./ProposalCard";

const proposal = (over: Partial<NoteView> = {}): NoteView => ({
  id: "p1",
  kind: "proposal",
  author: "claude",
  authorLabel: "Claude",
  origin: "mcp",
  status: "open",
  filePath: "main.py",
  lineStart: 2,
  lineEnd: 3,
  content: "Le signe est faux.",
  replacement: "    return a + b",
  before: "    return a - b",
  hintLevel: null,
  ...over,
});

const handlers = () => ({ busy: false, onAccept: vi.fn(), onReject: vi.fn() });

describe("ProposalCard", () => {
  it("shows before and after and disables accept when stale", () => {
    const { rerender } = render(<ProposalCard note={proposal()} {...handlers()} />);
    const before = screen.getByText("Before").closest("figure");
    const after = screen.getByText("After").closest("figure");
    expect(within(before as HTMLElement).getByText("return a - b")).toBeInTheDocument();
    expect(within(after as HTMLElement).getByText("return a + b")).toBeInTheDocument();
    expect(screen.getByText("main.py, lines 2 to 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept" })).toBeEnabled();

    rerender(<ProposalCard note={proposal({ status: "stale" })} {...handlers()} />);
    expect(screen.getByRole("button", { name: "Accept" })).toBeDisabled();
    expect(screen.getByText("The code has changed since")).toBeInTheDocument();
  });

  it("calls back on accept and reject, and waits while a decision is running", async () => {
    const calls = handlers();
    const user = userEvent.setup();
    const { rerender } = render(<ProposalCard note={proposal()} {...calls} />);
    await user.click(screen.getByRole("button", { name: "Accept" }));
    await user.click(screen.getByRole("button", { name: "Reject" }));
    expect(calls.onAccept).toHaveBeenCalledTimes(1);
    expect(calls.onReject).toHaveBeenCalledTimes(1);
    rerender(<ProposalCard note={proposal()} {...calls} busy />);
    await user.click(screen.getByRole("button", { name: "Accept" }));
    await user.click(screen.getByRole("button", { name: "Reject" }));
    expect(calls.onAccept).toHaveBeenCalledTimes(1);
    expect(calls.onReject).toHaveBeenCalledTimes(1);
    // « Occupé » ne retire pas les boutons du clavier : le focus ne tombe pas sur body.
    expect(screen.getByRole("button", { name: "Accept" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("button", { name: "Reject" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("says when the original passage is gone and hides buttons once decided", () => {
    const { rerender } = render(<ProposalCard note={proposal({ before: null })} {...handlers()} />);
    expect(
      screen.getByText("The original passage is no longer in the file."),
    ).toBeInTheDocument();
    rerender(<ProposalCard note={proposal({ status: "accepted" })} {...handlers()} />);
    expect(screen.getByText("Accepted")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
