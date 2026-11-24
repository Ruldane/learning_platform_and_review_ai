import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { applicationOut } from "@/test/applicationsApi";
import { openStream, renderApplications } from "@/test/applicationsHarness";
import { sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { apiError, recordPosts } from "@/test/councilHarness";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { applicationsManifest } from "../../manifest";
import { NewApplicationPage } from "./NewApplicationPage";

function setup(api: Parameters<typeof renderApplications>[2] = {}) {
  const sockets = createFakeSocketServer();
  const routes = applicationsManifest.routes.map((route) =>
    route.path === "candidatures/nouvelle"
      ? { path: route.path, element: <NewApplicationPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, "/candidatures/nouvelle", {
    applications: [applicationOut({ id: "a1" }), applicationOut({ id: "a9", title: "Autre" })],
    ...api,
  });
  return { ...view, sockets };
}

const field = (id: string, label: string, value: string, required = false) => ({
  id,
  label,
  required,
  max_length: 200,
  value,
});

const CONFIRM_FIELDS = [
  field("company", "Company", "Acme", true),
  field("title", "Role", "Data engineer", true),
  field("status", "Status", "applied", true),
  field("applied_on", "Application date (YYYY-MM-DD)", ""),
  field("channel", "Channel", "linkedin"),
  field("contact_name", "Contact", ""),
  field("contact_role", "Contact role", ""),
  field("notes", "Notes", ""),
];

/** Find the Tracking assistant's confirmation alongside the manual entry form. */
const confirmation = () => screen.findByRole("region", { name: /Create this application/ });

describe("NewApplicationPage, one-sentence entry", () => {
  beforeEach(() => useSessionStore.getState().reset("i1"));

  async function askConfirmation(over: Record<string, unknown> = {}) {
    const view = setup();
    await view.user.type(
      screen.getByLabelText("Your sentence"),
      "J'ai postulé hier chez Acme pour un poste de data engineer",
    );
    await view.user.click(screen.getByRole("button", { name: "Prepare the application" }));
    const stream = await openStream(view.sockets, "i1");
    const e = councilEvents("i1");
    stream.push(
      e.message("m1", "I found a data engineer application at Acme.", "tracker"),
      e.interrupt("application_confirm", "q1", {
        question: "Create this application ?",
        options: [
          { value: "create", label: "Create application" },
          { value: "cancel", label: "Cancel" },
        ],
        fields: CONFIRM_FIELDS,
        ...over,
      }),
    );
    return { ...view, stream, e };
  }

  it("starts the session with the sentence and shows the confirmation with the read values", async () => {
    const { state } = await askConfirmation();
    expect(state.intakes).toEqual([
      { text: "J'ai postulé hier chez Acme pour un poste de data engineer" },
    ]);
    const card = within(await confirmation());
    expect(card.getByLabelText("Company")).toHaveValue("Acme");
    expect(card.getByLabelText("Status")).toHaveDisplayValue("Applied");
    expect(card.getByLabelText("Application date (YYYY-MM-DD)")).toHaveAccessibleDescription(
      "Without a date, the application uses today's date.",
    );
  });

  it("answers with the choice and the fields, then opens the application the session announces", async () => {
    const resumes = recordPosts("/sessions/i1/resume", 200, sessionOut("i1", "running"));
    const { user, stream, e, router } = await askConfirmation();
    const card = within(await confirmation());
    const company = card.getByLabelText("Company");
    await user.clear(company);
    await user.type(company, "Acme Corp");
    await user.click(card.getByRole("button", { name: "Create application" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({
      interrupt_id: "q1",
      value: {
        choice: "create",
        fields: expect.objectContaining({ company: "Acme Corp", status: "applied" }),
      },
    });
    stream.push(e.artifactReady("application", "a1", "/candidatures/a1"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a1"));
  });

  it("offers to open the existing application or confirm a different role", async () => {
    const resumes = recordPosts("/sessions/i1/resume", 200, sessionOut("i1", "running"));
    const { user } = await askConfirmation({
      question: "Create this application ? You already have an application at Acme.",
      options: [
        { value: "distinct", label: "It's a different role" },
        { value: "open", label: "Open the existing application" },
        { value: "cancel", label: "Cancel" },
      ],
    });
    const card = within(await confirmation());
    expect(card.getByRole("button", { name: "It's a different role" })).toBeVisible();
    expect(card.queryByRole("button", { name: "Create application" })).toBeNull();
    await user.click(card.getByRole("button", { name: "Open the existing application" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "q1", value: "open" }]));
  });

  it("keeps January's edits and says why when the server asks the question again", async () => {
    recordPosts("/sessions/i1/resume", 200, sessionOut("i1", "running"));
    const { user, stream, e } = await askConfirmation();
    const first = within(await confirmation());
    await user.clear(first.getByLabelText("Company"));
    await user.type(first.getByLabelText("Company"), "Acme Corp");
    await user.type(first.getByLabelText("Application date (YYYY-MM-DD)"), "2099-01-01");
    await user.click(first.getByRole("button", { name: "Create application" }));
    // The server rejects the date and returns the original draft with a new interrupt ID.
    stream.push(
      e.interrupt("application_confirm", "q2", {
        question: "Create this application ?",
        options: [
          { value: "create", label: "Create application" },
          { value: "cancel", label: "Cancel" },
        ],
        fields: CONFIRM_FIELDS,
      }),
    );
    expect(await screen.findByText(/The date can't be in the future/)).toBeVisible();
    const again = within(
      (await screen.findAllByRole("region", { name: /Create this application/ })).at(-1)!,
    );
    expect(again.getByLabelText("Company")).toHaveValue("Acme Corp");
    expect(again.getByLabelText("Application date (YYYY-MM-DD)")).toHaveValue("2099-01-01");
    expect(again.getByRole("button", { name: "Create application" })).toBeEnabled();
  });

  it("opens the existing application announced by the session", async () => {
    const { stream, e, router } = await askConfirmation();
    stream.push(e.artifactReady("application", "a9", "/candidatures/a9"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a9"));
  });

  it("lets January edit her sentence after the session ends without a record", async () => {
    const { user, stream, e } = await askConfirmation();
    stream.push(e.failed("Your sentence is missing the company or the role."));
    expect(
      await screen.findByText("Your sentence is missing the company or the role."),
    ).toBeVisible();
    await user.click(await screen.findByRole("button", { name: "Write another sentence" }));
    expect(screen.getByLabelText("Your sentence")).toHaveValue(
      "J'ai postulé hier chez Acme pour un poste de data engineer",
    );
  });

  it("offers to resume or cancel a sentence session that is already open", async () => {
    let first = true;
    const { user, state } = setup({
      intake: () => {
        if (!first) return HttpResponse.json({ session_id: "i2" }, { status: 202 });
        first = false;
        return HttpResponse.json(
          apiError("intake_in_progress", "An entry is already open.", { session_id: "s9" }),
          { status: 409 },
        );
      },
    });
    await user.type(screen.getByLabelText("Your sentence"), "Une phrase");
    await user.click(screen.getByRole("button", { name: "Prepare the application" }));
    expect(await screen.findByText(/A one-sentence entry is already open/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Cancel this entry" }));
    await waitFor(() => expect(state.cancels).toEqual(["s9"]));
    await waitFor(() => expect(screen.queryByText(/already open/)).toBeNull());
    await user.click(screen.getByRole("button", { name: "Prepare the application" }));
    await waitFor(() => expect(state.intakes).toHaveLength(2));
  });

  it("resumes the open session when asked", async () => {
    const { user, sockets } = setup({
      intake: () =>
        HttpResponse.json(
          apiError("intake_in_progress", "An entry is already open.", { session_id: "s9" }),
          { status: 409 },
        ),
    });
    await user.type(screen.getByLabelText("Your sentence"), "Une phrase");
    await user.click(screen.getByRole("button", { name: "Prepare the application" }));
    await user.click(await screen.findByRole("button", { name: "Resume this entry" }));
    await openStream(sockets, "s9");
  });

  it("does not send an empty sentence", async () => {
    const { state } = setup();
    expect(screen.getByRole("button", { name: "Prepare the application" })).toBeDisabled();
    expect(state.intakes).toHaveLength(0);
  });
});
