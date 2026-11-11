import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { row } from "../viewFixtures";
import { PendingDecisions } from "./PendingDecisions";

const decision = row({
  id: "d1",
  kind: "decision",
  title: "Viser le NLP",
  created_by: "strategist",
  status: "pending",
  reason: "Tu as dit vouloir te spécialiser.",
});

describe("PendingDecisions", () => {
  it("confirms and rejects", async () => {
    const onConfirm = vi.fn();
    const onReject = vi.fn();
    const user = userEvent.setup();
    render(
      <PendingDecisions
        items={[decision]}
        busyId={null}
        onConfirm={onConfirm}
        onReject={onReject}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Confirmer" }));
    expect(onConfirm).toHaveBeenCalledWith("d1");
    await user.click(screen.getByRole("button", { name: "Refuser" }));
    expect(onReject).toHaveBeenCalledWith("d1");
  });

  it("shows the title, the proposing agent and the reason", () => {
    render(
      <PendingDecisions items={[decision]} busyId={null} onConfirm={vi.fn()} onReject={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: "À confirmer" })).toBeInTheDocument();
    expect(screen.getByText("Viser le NLP")).toBeInTheDocument();
    expect(screen.getByText("Proposé par Stratège")).toBeInTheDocument();
    expect(screen.getByText("Tu as dit vouloir te spécialiser.")).toBeInTheDocument();
  });

  it("locks only the buttons of the busy decision", () => {
    const other = row({ id: "d2", kind: "decision", title: "Autre", status: "pending" });
    render(
      <PendingDecisions
        items={[decision, other]}
        busyId="d1"
        onConfirm={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    const confirms = screen.getAllByRole("button", { name: "Confirmer" });
    expect(confirms[0]).toBeDisabled();
    expect(confirms[1]).toBeEnabled();
  });

  it("shows an empty message and no button", () => {
    render(<PendingDecisions items={[]} busyId={null} onConfirm={vi.fn()} onReject={vi.fn()} />);
    expect(screen.getByText("Aucune décision en attente.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
