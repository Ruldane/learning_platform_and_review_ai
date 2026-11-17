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
    const before = screen.getByText("Avant").closest("figure");
    const after = screen.getByText("Après").closest("figure");
    expect(within(before as HTMLElement).getByText("return a - b")).toBeInTheDocument();
    expect(within(after as HTMLElement).getByText("return a + b")).toBeInTheDocument();
    expect(screen.getByText("main.py, lignes 2 à 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accepter" })).toBeEnabled();

    rerender(<ProposalCard note={proposal({ status: "stale" })} {...handlers()} />);
    expect(screen.getByRole("button", { name: "Accepter" })).toBeDisabled();
    expect(screen.getByText("Le code a changé depuis")).toBeInTheDocument();
  });

  it("calls back on accept and reject, and waits while a decision is running", async () => {
    const calls = handlers();
    const user = userEvent.setup();
    const { rerender } = render(<ProposalCard note={proposal()} {...calls} />);
    await user.click(screen.getByRole("button", { name: "Accepter" }));
    await user.click(screen.getByRole("button", { name: "Refuser" }));
    expect(calls.onAccept).toHaveBeenCalledTimes(1);
    expect(calls.onReject).toHaveBeenCalledTimes(1);
    rerender(<ProposalCard note={proposal()} {...calls} busy />);
    await user.click(screen.getByRole("button", { name: "Accepter" }));
    await user.click(screen.getByRole("button", { name: "Refuser" }));
    expect(calls.onAccept).toHaveBeenCalledTimes(1);
    expect(calls.onReject).toHaveBeenCalledTimes(1);
    // « Occupé » ne retire pas les boutons du clavier : le focus ne tombe pas sur body.
    expect(screen.getByRole("button", { name: "Accepter" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("button", { name: "Refuser" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("says when the original passage is gone and hides buttons once decided", () => {
    const { rerender } = render(<ProposalCard note={proposal({ before: null })} {...handlers()} />);
    expect(
      screen.getByText("Le passage d'origine n'est plus dans le fichier."),
    ).toBeInTheDocument();
    rerender(<ProposalCard note={proposal({ status: "accepted" })} {...handlers()} />);
    expect(screen.getByText("Acceptée")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
