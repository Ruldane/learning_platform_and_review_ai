import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { applicationOut, eventOut, reminderOut } from "@/test/applicationsApi";
import { renderApplications } from "@/test/applicationsHarness";
import { todayString } from "../../dates";
import { applicationsManifest } from "../../manifest";

const routes = applicationsManifest.routes;
// Use a fresh record per test because the fake API mutates its rows.
const todo = () =>
  applicationOut({
    id: "a2",
    company: "Beta",
    title: "Analyste",
    status: "to_apply",
    applied_on: null,
    due_reminders: 0,
    cv_version_number: null,
  });

function setup(path = "/applications/a1", api: Parameters<typeof renderApplications>[2] = {}) {
  return renderApplications(routes, path, {
    applications: [applicationOut({ cv_version_number: 2 }), todo()],
    ...api,
  });
}

async function openDrawer(path?: string, api?: Parameters<typeof renderApplications>[2]) {
  const view = setup(path, api);
  const dialog = await screen.findByRole("dialog", { name: /,/ });
  await within(dialog).findByLabelText("Company");
  return { ...view, dialog };
}

describe("ApplicationDrawer", () => {
  it("shows the application: fields, contacts, history, version and tools", async () => {
    const { dialog } = await openDrawer("/applications/a1", {
      details: {
        a1: {
          events: [
            eventOut(),
            eventOut({
              id: "e2",
              kind: "note",
              at: "2026-11-05T10:00:00Z",
              text: "Appel avec la RH",
            }),
          ],
        },
      },
    });
    expect(dialog).toHaveAccessibleName("Acme, Data engineer");
    expect(within(dialog).getByLabelText("Company")).toHaveValue("Acme");
    expect(within(dialog).getByLabelText("Notes")).toHaveValue("Premier échange par téléphone.");
    expect(within(dialog).getByLabelText("Name, contact 1")).toHaveValue("Camille Durand");
    expect(within(dialog).getByText("Appel avec la RH")).toBeVisible();
    expect(within(dialog).getByText("Résumé version 2")).toBeVisible();
    expect(within(dialog).getByRole("link", { name: "See my résumé versions" })).toHaveAttribute(
      "href",
      "/career/cv/versions",
    );
    expect(within(dialog).getByRole("link", { name: "Application kit" })).toHaveAttribute(
      "href",
      "/applications/a1/kit",
    );
    expect(within(dialog).getByRole("link", { name: "Practice interview" })).toHaveAttribute(
      "href",
      "/applications/a1/interview",
    );
    expect(within(dialog).getByRole("link", { name: "Hiring committee" })).toHaveAttribute(
      "href",
      "/applications/a1/committee",
    );
  });

  it("saves only the fields that changed", async () => {
    const { user, state, dialog } = await openDrawer();
    const title = within(dialog).getByLabelText("Role");
    await user.clear(title);
    await user.type(title, "Data engineer senior");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(state.patches).toEqual([{ id: "a1", body: { title: "Data engineer senior" } }]);
    expect(await within(dialog).findByText("Application saved.")).toBeVisible();
    expect(dialog).toHaveAccessibleName("Acme, Data engineer senior");
  });

  it("keeps unsaved edits when another write in the drawer re-reads the application", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    const title = within(dialog).getByLabelText("Role");
    await user.clear(title);
    await user.type(title, "Analyste senior");
    await user.type(within(dialog).getByLabelText("Note"), "Rappeler jeudi");
    await user.click(within(dialog).getByRole("button", { name: "Add the note" }));
    await within(dialog).findByText("Note added.");
    expect(within(dialog).getByLabelText("Role")).toHaveValue("Analyste senior");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(state.patches).toEqual([{ id: "a2", body: { title: "Analyste senior" } }]);
  });

  it("takes the date a status change sets, and never sends it back as an edit", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    expect(within(dialog).getByLabelText("Applied on")).toHaveValue("");
    const company = within(dialog).getByLabelText("Company");
    await user.clear(company);
    await user.type(company, "Beta SAS");
    await user.click(within(dialog).getByRole("button", { name: "I applied" }));
    await within(dialog).findByText("Status changed: Applied.");
    expect(within(dialog).getByLabelText("Applied on")).toHaveValue(todayString());
    expect(within(dialog).getByLabelText("Company")).toHaveValue("Beta SAS");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(state.patches).toEqual([{ id: "a2", body: { company: "Beta SAS" } }]);
  });

  it("clears the unsaved mark once its own save went through", async () => {
    const { user, dialog } = await openDrawer();
    const title = within(dialog).getByLabelText("Role");
    await user.clear(title);
    await user.type(title, "Data engineer senior");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    await within(dialog).findByText("Application saved.");
    expect(within(dialog).getByLabelText("Role")).toHaveValue("Data engineer senior");
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("clears an optional field with null", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.clear(within(dialog).getByLabelText("Notes"));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(state.patches[0]?.body).toEqual({ notes: null });
  });

  it("refuses an empty company and says so on the field", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.clear(within(dialog).getByLabelText("Company"));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(state.patches).toHaveLength(0);
    expect(within(dialog).getByLabelText("Company")).toBeInvalid();
    expect(within(dialog).getByText("Required.")).toBeVisible();
  });

  it("refuses a contact without a name", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.click(within(dialog).getByRole("button", { name: "Add a contact" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(state.patches).toHaveLength(0);
    expect(within(dialog).getByText("Each contact needs a name.")).toBeVisible();
  });

  it("saves the contacts, replacing the list", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.click(within(dialog).getByRole("button", { name: "Add a contact" }));
    await user.type(within(dialog).getByLabelText("Name, contact 2"), "Sam Martin");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(state.patches[0]?.body).toEqual({
      contacts: [
        { name: "Camille Durand", role: "Responsable data", url: null },
        { name: "Sam Martin", role: null, url: null },
      ],
    });
  });

  it("records the application using today's date by default", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    await user.click(within(dialog).getByRole("button", { name: "I applied" }));
    expect(state.events).toEqual([
      { id: "a2", body: { kind: "status", status: "applied", on: todayString() } },
    ]);
    expect(await within(dialog).findByText("Status changed: Applied.")).toBeVisible();
    expect(within(dialog).queryByRole("button", { name: "I applied" })).toBeNull();
  });

  it("records the application using the chosen date", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    const day = within(dialog).getByLabelText("Application date");
    await user.clear(day);
    await user.type(day, "2026-11-10");
    await user.click(within(dialog).getByRole("button", { name: "I applied" }));
    expect(state.events[0]?.body).toEqual({ kind: "status", status: "applied", on: "2026-11-10" });
  });

  it("rejects future dates for applications and status changes", async () => {
    const { user, state, dialog } = await openDrawer("/applications/a2");
    const applied = within(dialog).getByLabelText("Application date");
    expect(applied).toHaveAttribute("max", todayString());
    expect(within(dialog).getByLabelText("Date of change")).toHaveAttribute(
      "max",
      todayString(),
    );
    await user.clear(applied);
    await user.type(applied, "2999-01-01");
    await user.click(within(dialog).getByRole("button", { name: "I applied" }));
    expect(within(dialog).getByText("This date is in the future.")).toBeVisible();
    const changed = within(dialog).getByLabelText("Date of change");
    await user.clear(changed);
    await user.type(changed, "2999-01-01");
    await user.click(within(dialog).getByRole("button", { name: "Change status" }));
    expect(within(dialog).getAllByText("This date is in the future.")).toHaveLength(2);
    expect(state.events).toEqual([]);
  });

  it("changes the status and records the interview date", async () => {
    const { user, state, dialog } = await openDrawer();
    expect(within(dialog).queryByRole("option", { name: "Applied" })).toBeNull();
    await user.selectOptions(within(dialog).getByLabelText("New status"), "interview");
    await user.type(within(dialog).getByLabelText("Interview date"), "2026-11-25");
    await user.click(within(dialog).getByRole("button", { name: "Change status" }));
    expect(state.events[0]).toEqual({
      id: "a1",
      body: { kind: "status", status: "interview", on: todayString(), interview_on: "2026-11-25" },
    });
    expect(await within(dialog).findByText("Status changed: Interview.")).toBeVisible();
  });

  it("lets January add missing posting text for the application kit", async () => {
    const { user, state, dialog } = await openDrawer();
    expect(within(dialog).getByText(/This application has no posting text/)).toBeVisible();
    const add = within(dialog).getByRole("button", { name: "Add the posting text" });
    expect(add).toBeDisabled();
    await user.type(
      within(dialog).getByLabelText("Posting text"),
      "Nous cherchons une data engineer.",
    );
    await user.click(add);
    expect(state.patches).toEqual([
      { id: "a1", body: { posting_text: "Nous cherchons une data engineer." } },
    ]);
    expect(await within(dialog).findByText(/The posting text is saved/)).toBeVisible();
    expect(
      within(dialog).queryByRole("button", { name: "Add the posting text" }),
    ).toBeNull();
  });

  it("hides the posting text field when the application already has text", async () => {
    const { dialog } = await openDrawer("/applications/a1", {
      details: { a1: { posting_text: "Texte déjà là." } },
    });
    expect(within(dialog).queryByLabelText("Posting text")).toBeNull();
    expect(within(dialog).getByText(/The posting text is saved/)).toBeVisible();
  });

  it("adds a note to the history", async () => {
    const { user, state, dialog } = await openDrawer();
    await user.type(within(dialog).getByLabelText("Note"), "Rappeler jeudi");
    await user.click(within(dialog).getByRole("button", { name: "Add the note" }));
    expect(state.events[0]).toEqual({ id: "a1", body: { kind: "note", text: "Rappeler jeudi" } });
    expect(await within(dialog).findByText("Note added.")).toBeVisible();
    expect(within(dialog).getByLabelText("Note")).toHaveValue("");
  });

  it("lists the pending reminders of the application and handles them", async () => {
    const reminders = [reminderOut(), reminderOut({ id: "r9", application_id: "a2" })];
    const { user, state, dialog } = await openDrawer("/applications/a1", { reminders });
    const card = await within(dialog).findByRole("article");
    expect(within(card).getByText("LinkedIn follow-up after 7 days")).toBeVisible();
    await user.click(within(card).getByRole("button", { name: "Done" }));
    expect(state.reminderActions).toEqual([{ id: "r1", action: "done" }]);
    expect(
      await within(dialog).findByText("No pending follow-ups for this application."),
    ).toBeVisible();
  });

  it("shows an error when the server refuses a write", async () => {
    const { user, dialog } = await openDrawer("/applications/a1", {
      event: () =>
        new Response(
          JSON.stringify({
            error: { code: "validation_error", message: "Date invalide.", details: null },
          }),
          {
            status: 422,
            headers: { "content-type": "application/json" },
          },
        ),
    });
    await user.type(within(dialog).getByLabelText("Note"), "x");
    await user.click(within(dialog).getByRole("button", { name: "Add the note" }));
    expect(await within(dialog).findByText("Date invalide.")).toBeVisible();
  });

  it("closes with Escape and goes back to the board", async () => {
    const { user, router } = await openDrawer();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("closes with its button", async () => {
    const { user, router, dialog } = await openDrawer();
    await user.click(within(dialog).getByRole("button", { name: "Close the application" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications"));
  });

  it("says when the application does not exist, and goes back to the board", async () => {
    const { user, router } = setup("/applications/inconnue");
    expect(await screen.findByText("Application not found")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Back to tracking" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications"));
  });
});
