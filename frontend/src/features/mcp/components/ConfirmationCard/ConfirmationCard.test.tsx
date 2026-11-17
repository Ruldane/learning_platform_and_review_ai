import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ConfirmationView } from "../viewTypes";
import { ConfirmationCard } from "./ConfirmationCard";

const view = (over: Partial<ConfirmationView> = {}): ConfirmationView => ({
  id: "cf1",
  summary: "Ajouter au profil maître : « Migration vers dbt ».",
  action: "cv_master_profile_draft",
  tokenLabel: "Claude Code (portable)",
  state: "pending",
  expiresAt: "2099-11-18T10:00:00Z",
  decidedAt: null,
  verdict: { ok: false, reasons: ["Aucune preuve dans ton profil."], summary: null },
  ...over,
});

function setup(confirmation: ConfirmationView, busy = false) {
  const onConfirm = vi.fn();
  const onRefuse = vi.fn();
  render(
    <ConfirmationCard
      confirmation={confirmation}
      busy={busy}
      onConfirm={onConfirm}
      onRefuse={onRefuse}
    />,
  );
  return { onConfirm, onRefuse, user: userEvent.setup() };
}

describe("ConfirmationCard", () => {
  it("confirmation card shows verdict and both buttons", async () => {
    const { onConfirm, onRefuse, user } = setup(view());
    expect(screen.getByText("Ajouter au profil maître : « Migration vers dbt »."));
    expect(screen.getByText("Contrôle d'honnêteté")).toBeInTheDocument();
    expect(screen.getByText("Réserves :")).toBeInTheDocument();
    expect(screen.getByText("Aucune preuve dans ton profil.")).toBeInTheDocument();
    expect(screen.getByText(/Claude Code \(portable\)/)).toBeInTheDocument();
    expect(screen.getByText(/Expire le/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmer" }));
    await user.click(screen.getByRole("button", { name: "Refuser" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onRefuse).toHaveBeenCalledTimes(1);
  });

  it("a verdict without reserve says so", () => {
    setup(view({ verdict: { ok: true, reasons: [], summary: "Tient face au profil." } }));
    expect(screen.getByText("Aucune réserve.")).toBeInTheDocument();
    expect(screen.getByText("Tient face au profil.")).toBeInTheDocument();
  });

  it("a request without precheck never claims it was checked", () => {
    setup(view({ verdict: null }));
    expect(screen.getByText("Pas de contrôle préalable pour cette action.")).toBeInTheDocument();
    expect(screen.queryByText("Aucune réserve.")).toBeNull();
  });

  it("expired confirmation has no buttons", () => {
    setup(view({ state: "expired" }));
    expect(screen.getByText("Expirée")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it.each(["confirmed", "refused", "failed"] as const)("a %s request has no buttons", (state) => {
    setup(view({ state, decidedAt: "2026-11-17T11:00:00Z" }));
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("disables both buttons while a decision is in flight", () => {
    setup(view(), true);
    expect(screen.getByRole("button", { name: "Confirmer" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Refuser" })).toBeDisabled();
  });
});
