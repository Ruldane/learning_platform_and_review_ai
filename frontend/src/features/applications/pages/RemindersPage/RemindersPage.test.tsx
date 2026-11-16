import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { applicationOut, reminderOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { apiError } from "@/test/councilHarness";
import { expectCoherentOutline } from "@/test/headingOutline";
import { applicationsManifest } from "../../manifest";

const routes = applicationsManifest.routes;

const REMINDERS = () => [
  reminderOut({ id: "r1", draft: "Bonjour Camille, une petite relance." }),
  reminderOut({
    id: "r2",
    application_id: "a2",
    kind: "close_21",
    company: "Beta",
    title: "Analyste",
    contact: null,
    due_on: "2026-11-12",
    draft: "Beta ne t'a pas répondu : tu classes la fiche ?",
  }),
];

function setup(api: Parameters<typeof renderApplications>[2] = {}) {
  return renderApplications(routes, "/candidatures/relances", {
    applications: [
      applicationOut(),
      applicationOut({ id: "a2", company: "Beta", title: "Analyste", status: "followed_up" }),
    ],
    reminders: REMINDERS(),
    ...api,
  });
}

const cardOf = async (title: string) => {
  const heading = await screen.findByRole("heading", { name: title });
  return within(heading.closest("article") as HTMLElement);
};

describe("RemindersPage", () => {
  it("has one h1, then one h2 per reminder (one h1 per applications page)", async () => {
    setup();
    await cardOf("Relance LinkedIn à 7 jours");
    expectCoherentOutline();
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(2);
    expect(screen.queryByRole("heading", { level: 3 })).toBeNull();
  });

  it("disables Fait, Reporter and Ignorer on every card while an action runs (reminder buttons disabled while pending)", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const { user } = setup({
      reminderAction: async () => {
        await gate;
        return undefined;
      },
    });
    const card = await cardOf("Relance LinkedIn à 7 jours");
    expect(
      screen.getAllByRole("article").every((a) => a.getAttribute("aria-busy") === "false"),
    ).toBe(true);
    await user.click(card.getByRole("button", { name: "Reporter de 3 jours" }));
    await waitFor(() =>
      expect(screen.getAllByRole("article")[0]).toHaveAttribute("aria-busy", "true"),
    );
    for (const name of ["Fait", "Classer en Sans réponse", "Reporter de 3 jours", "Ignorer"]) {
      for (const button of screen.getAllByRole("button", { name }))
        expect(button).toHaveAttribute("aria-disabled", "true");
    }
    expect(card.getByRole("button", { name: "Copier" })).toBeEnabled();
    release();
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Ignorer" })[0]).toHaveAttribute(
        "aria-disabled",
        "false",
      ),
    );
    expect(screen.getAllByRole("article")[0]).toHaveAttribute("aria-busy", "false");
  });

  it("keeps the focus on the action button when the action fails", async () => {
    const { user } = setup({
      reminderAction: () =>
        HttpResponse.json(apiError("internal_error", "Panne."), { status: 500 }),
    });
    const card = await cardOf("Relance LinkedIn à 7 jours");
    const postpone = card.getByRole("button", { name: "Reporter de 3 jours" });
    await user.click(postpone);
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(postpone).toHaveFocus();
  });

  it("lists the due reminders with who to contact and the draft", async () => {
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: "Relances" })).toBeVisible();
    const linkedin = await cardOf("Relance LinkedIn à 7 jours");
    expect(linkedin.getByText("Camille Durand, Responsable data")).toBeVisible();
    expect(linkedin.getByText("Bonjour Camille, une petite relance.")).toBeVisible();
    expect(screen.getAllByText(/Rien n'est envoyé par l'application/)).toHaveLength(2);
  });

  it("copies the draft to the clipboard and confirms it", async () => {
    const { user } = setup();
    const card = await cardOf("Relance LinkedIn à 7 jours");
    await user.click(card.getByRole("button", { name: "Copier" }));
    expect(await card.findByText("Brouillon copié.")).toBeVisible();
    expect(await navigator.clipboard.readText()).toBe("Bonjour Camille, une petite relance.");
  });

  it("says when the clipboard is not available", async () => {
    const { user } = setup();
    const card = await cardOf("Relance LinkedIn à 7 jours");
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("denied"));
    await user.click(card.getByRole("button", { name: "Copier" }));
    expect(await card.findByText(/Copie impossible/)).toBeVisible();
  });

  it("marks a reminder as done: it leaves the list, it is announced and the focus moves up", async () => {
    const { user, state } = setup();
    const card = await cardOf("Relance LinkedIn à 7 jours");
    await user.click(card.getByRole("button", { name: "Fait" }));
    expect(state.reminderActions).toEqual([{ id: "r1", action: "done" }]);
    await waitFor(() => expect(screen.queryByText("Relance LinkedIn à 7 jours")).toBeNull());
    expect(screen.getByText("Relance traitée.")).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Relances" })).toHaveFocus();
    expect(screen.getByText("Classer la fiche ?")).toBeVisible();
  });

  it("postpones a reminder by three days", async () => {
    const { user, state } = setup();
    const card = await cardOf("Relance LinkedIn à 7 jours");
    await user.click(card.getByRole("button", { name: "Reporter de 3 jours" }));
    expect(state.reminderActions).toEqual([{ id: "r1", action: "postpone" }]);
    expect(await screen.findByText("Relance traitée.")).toBeVisible();
  });

  it("ignores a reminder", async () => {
    const { user, state } = setup();
    const card = await cardOf("Relance LinkedIn à 7 jours");
    await user.click(card.getByRole("button", { name: "Ignorer" }));
    expect(state.reminderActions).toEqual([{ id: "r1", action: "ignore" }]);
    await waitFor(() => expect(screen.queryByText("Relance LinkedIn à 7 jours")).toBeNull());
  });

  it("files the application as Sans réponse for the last reminder, then closes the reminder", async () => {
    const { user, state, rows } = setup();
    const card = await cardOf("Classer la fiche ?");
    await user.click(card.getByRole("button", { name: "Classer en Sans réponse" }));
    await waitFor(() => expect(state.reminderActions).toEqual([{ id: "r2", action: "done" }]));
    expect(state.events).toEqual([{ id: "a2", body: { kind: "status", status: "no_answer" } }]);
    expect(rows.find((row) => row.id === "a2")?.status).toBe("no_answer");
    expect(await screen.findByText("Fiche classée en Sans réponse.")).toBeVisible();
    expect(screen.queryByText("Classer la fiche ?")).toBeNull();
  });

  it("is happy when the status change already closed the reminder", async () => {
    const { user } = setup({
      reminderAction: () =>
        HttpResponse.json(apiError("reminder_closed", "Déjà traitée."), { status: 409 }),
    });
    const card = await cardOf("Classer la fiche ?");
    await user.click(card.getByRole("button", { name: "Classer en Sans réponse" }));
    expect(await screen.findByText("Fiche classée en Sans réponse.")).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps the card and says why when the server refuses", async () => {
    const { user } = setup({
      reminderAction: () =>
        HttpResponse.json(apiError("internal_error", "Le serveur ne répond pas."), { status: 500 }),
    });
    const card = await cardOf("Relance LinkedIn à 7 jours");
    await user.click(card.getByRole("button", { name: "Fait" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur ne répond pas.");
    expect(screen.getByText("Relance LinkedIn à 7 jours")).toBeVisible();
  });

  it("says there is nothing to do when no reminder is due", async () => {
    const { user, router } = setup({ reminders: [] });
    expect(await screen.findByText("Aucune relance due")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Retour au suivi" }));
    expect(router.state.location.pathname).toBe("/candidatures");
  });

  it("says it is loading", () => {
    setup();
    expect(screen.getByText("Chargement des relances…")).toBeVisible();
  });

  it("shows an error with a retry when the reminders cannot be read", async () => {
    let calls = 0;
    const { user } = setup({
      reminderList: () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(apiError("internal_error", "Le serveur ne répond pas."), {
              status: 500,
            })
          : HttpResponse.json(REMINDERS());
      },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur ne répond pas.");
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await cardOf("Relance LinkedIn à 7 jours")).toBeTruthy();
  });
});
