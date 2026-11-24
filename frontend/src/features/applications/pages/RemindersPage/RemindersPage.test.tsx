import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { applicationOut, reminderOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { apiError } from "@/test/councilHarness";
import { expectCoherentOutline } from "@/test/headingOutline";
import { applicationsManifest } from "../../manifest";

const routes = applicationsManifest.routes;
const LINKEDIN_FOLLOW_UP = "LinkedIn follow-up after 7 days";
const CLOSE_APPLICATION = "Close the application?";
const POSTPONE = "Postpone 3 days";

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
  return renderApplications(routes, "/applications/reminders", {
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
    await cardOf(LINKEDIN_FOLLOW_UP);
    expectCoherentOutline();
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(2);
    expect(screen.queryByRole("heading", { level: 3 })).toBeNull();
  });

  it("disables actions on every card while a reminder update is pending", async () => {
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
    const card = await cardOf(LINKEDIN_FOLLOW_UP);
    expect(
      screen.getAllByRole("article").every((a) => a.getAttribute("aria-busy") === "false"),
    ).toBe(true);
    await user.click(card.getByRole("button", { name: POSTPONE }));
    await waitFor(() =>
      expect(screen.getAllByRole("article")[0]).toHaveAttribute("aria-busy", "true"),
    );
    for (const name of ["Done", "Mark as No answer", POSTPONE, "Ignore"]) {
      for (const button of screen.getAllByRole("button", { name }))
        expect(button).toHaveAttribute("aria-disabled", "true");
    }
    expect(card.getByRole("button", { name: "Copy" })).toBeEnabled();
    release();
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Ignore" })[0]).toHaveAttribute(
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
    const card = await cardOf(LINKEDIN_FOLLOW_UP);
    const postpone = card.getByRole("button", { name: POSTPONE });
    await user.click(postpone);
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(postpone).toHaveFocus();
  });

  it("lists the due reminders with who to contact and the draft", async () => {
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: "Follow-ups" })).toBeVisible();
    const linkedin = await cardOf(LINKEDIN_FOLLOW_UP);
    expect(linkedin.getByText("Camille Durand, Responsable data")).toBeVisible();
    expect(linkedin.getByText("Bonjour Camille, une petite relance.")).toBeVisible();
    expect(screen.getAllByText(/The app sends nothing: copy it/)).toHaveLength(2);
  });

  it("copies the draft to the clipboard and confirms it", async () => {
    const { user } = setup();
    const card = await cardOf(LINKEDIN_FOLLOW_UP);
    await user.click(card.getByRole("button", { name: "Copy" }));
    expect(await card.findByText("Draft copied.")).toBeVisible();
    expect(await navigator.clipboard.readText()).toBe("Bonjour Camille, une petite relance.");
  });

  it("says when the clipboard is not available", async () => {
    const { user } = setup();
    const card = await cardOf(LINKEDIN_FOLLOW_UP);
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("denied"));
    await user.click(card.getByRole("button", { name: "Copy" }));
    expect(await card.findByText(/Can't copy/)).toBeVisible();
  });

  it("announces completion and moves focus to the heading when a reminder is done", async () => {
    const { user, state } = setup();
    const card = await cardOf(LINKEDIN_FOLLOW_UP);
    await user.click(card.getByRole("button", { name: "Done" }));
    expect(state.reminderActions).toEqual([{ id: "r1", action: "done" }]);
    await waitFor(() => expect(screen.queryByText(LINKEDIN_FOLLOW_UP)).toBeNull());
    expect(screen.getByText("Follow-up handled.")).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Follow-ups" })).toHaveFocus();
    expect(screen.getByText(CLOSE_APPLICATION)).toBeVisible();
  });

  it("postpones a reminder by three days", async () => {
    const { user, state } = setup();
    const card = await cardOf(LINKEDIN_FOLLOW_UP);
    await user.click(card.getByRole("button", { name: POSTPONE }));
    expect(state.reminderActions).toEqual([{ id: "r1", action: "postpone" }]);
    expect(await screen.findByText("Follow-up handled.")).toBeVisible();
  });

  it("ignores a reminder", async () => {
    const { user, state } = setup();
    const card = await cardOf(LINKEDIN_FOLLOW_UP);
    await user.click(card.getByRole("button", { name: "Ignore" }));
    expect(state.reminderActions).toEqual([{ id: "r1", action: "ignore" }]);
    await waitFor(() => expect(screen.queryByText(LINKEDIN_FOLLOW_UP)).toBeNull());
  });

  it("marks the application as No answer and closes the last reminder", async () => {
    const { user, state, rows } = setup();
    const card = await cardOf(CLOSE_APPLICATION);
    await user.click(card.getByRole("button", { name: "Mark as No answer" }));
    await waitFor(() => expect(state.reminderActions).toEqual([{ id: "r2", action: "done" }]));
    expect(state.events).toEqual([{ id: "a2", body: { kind: "status", status: "no_answer" } }]);
    expect(rows.find((row) => row.id === "a2")?.status).toBe("no_answer");
    expect(await screen.findByText("Application marked as No answer.")).toBeVisible();
    expect(screen.queryByText(CLOSE_APPLICATION)).toBeNull();
  });

  it("is happy when the status change already closed the reminder", async () => {
    const { user } = setup({
      reminderAction: () =>
        HttpResponse.json(apiError("reminder_closed", "Déjà traitée."), { status: 409 }),
    });
    const card = await cardOf(CLOSE_APPLICATION);
    await user.click(card.getByRole("button", { name: "Mark as No answer" }));
    expect(await screen.findByText("Application marked as No answer.")).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps the card and says why when the server refuses", async () => {
    const { user } = setup({
      reminderAction: () =>
        HttpResponse.json(apiError("internal_error", "Le serveur ne répond pas."), { status: 500 }),
    });
    const card = await cardOf(LINKEDIN_FOLLOW_UP);
    await user.click(card.getByRole("button", { name: "Done" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur ne répond pas.");
    expect(screen.getByText(LINKEDIN_FOLLOW_UP)).toBeVisible();
  });

  it("says there is nothing to do when no reminder is due", async () => {
    const { user, router } = setup({ reminders: [] });
    expect(await screen.findByText("No follow-ups due")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Back to tracking" }));
    expect(router.state.location.pathname).toBe("/applications");
  });

  it("says it is loading", () => {
    setup();
    expect(screen.getByText("Loading follow-ups…")).toBeVisible();
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
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await cardOf(LINKEDIN_FOLLOW_UP)).toBeTruthy();
  });
});
