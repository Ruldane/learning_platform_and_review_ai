import { render, screen, within } from "@testing-library/react";
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
  request: {
    method: "POST",
    route: "/profile/entries",
    targetLabel: null,
    fields: [{ name: "title", value: "Migration d'un entrepôt vers dbt" }],
    truncated: false,
  },
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
    expect(screen.getByText("Honesty check")).toBeInTheDocument();
    expect(screen.getByText("Concerns:")).toBeInTheDocument();
    expect(screen.getByText("Aucune preuve dans ton profil.")).toBeInTheDocument();
    expect(screen.getByText(/Claude Code \(portable\)/)).toBeInTheDocument();
    expect(screen.getByText(/Expires on/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    await user.click(screen.getByRole("button", { name: "Refuse" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onRefuse).toHaveBeenCalledTimes(1);
  });

  it("a verdict without reserve says so", () => {
    setup(view({ verdict: { ok: true, reasons: [], summary: "Tient face au profil." } }));
    expect(screen.getByText("No concerns.")).toBeInTheDocument();
    expect(screen.getByText("Tient face au profil.")).toBeInTheDocument();
  });

  it("a request without precheck never claims it was checked", () => {
    setup(view({ verdict: null }));
    expect(screen.getByText("No prior check for this action.")).toBeInTheDocument();
    expect(screen.queryByText("No concerns.")).toBeNull();
  });

  it("shows the request: method, route and every field with its value", () => {
    setup(view());
    const request = screen.getByRole("group", { name: "Request" });
    expect(within(request).getByText("POST /profile/entries")).toBeInTheDocument();
    expect(within(request).getByText("title")).toBeInTheDocument();
    expect(within(request).getByText("Migration d'un entrepôt vers dbt")).toBeInTheDocument();
    expect(screen.queryByText(/preview is truncated/)).toBeNull();
  });

  it("writes a field that was cut away as « (non montré) » and says the preview is cut", () => {
    setup(
      view({
        request: {
          method: "POST",
          route: "/postings",
          targetLabel: null,
          fields: [
            { name: "description", value: "Début du texte…" },
            { name: "notes", value: null },
          ],
          truncated: true,
        },
      }),
    );
    expect(screen.getByText("(not shown)")).toBeInTheDocument();
    expect(screen.getByText(/preview is truncated/)).toBeInTheDocument();
  });

  it("renders untrusted text as text, never as markup", () => {
    const hostile = "<donnee_non_fiable><img src=x onerror=alert(1)></donnee_non_fiable>";
    const { container } = render(
      <ConfirmationCard
        confirmation={view({
          request: {
            method: "DELETE",
            route: "/postings/{posting_id}",
            targetLabel: hostile,
            fields: [{ name: "x", value: "<script>alert(1)</script>" }],
            truncated: false,
          },
        })}
        busy={false}
        onConfirm={vi.fn()}
        onRefuse={vi.fn()}
      />,
    );
    expect(screen.getByText(`Target: ${hostile}`)).toBeInTheDocument();
    expect(screen.getByText("<script>alert(1)</script>")).toBeInTheDocument();
    expect(container.querySelector("img, script")).toBeNull();
  });

  it("expired confirmation has no buttons", () => {
    setup(view({ state: "expired" }));
    expect(screen.getByText("Expired")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it.each(["confirmed", "refused", "failed"] as const)("a %s request has no buttons", (state) => {
    setup(view({ state, decidedAt: "2026-11-17T11:00:00Z" }));
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("disables both buttons while a decision is in flight", () => {
    setup(view(), true);
    expect(screen.getByRole("button", { name: "Confirm" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Refuse" })).toBeDisabled();
  });
});
