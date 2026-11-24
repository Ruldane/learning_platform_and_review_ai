import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { applicationOut } from "@/test/applicationsApi";
import { openStream, renderApplications } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { interviewApi, interviewOut, type InterviewApiOptions } from "@/test/interviewApi";
import { postingOut } from "@/test/postingsApi";
import { server } from "@/test/server";
import { applicationsManifest } from "../../manifest";
import { FreeInterviewPage } from "./FreeInterviewPage";

const ROUTE = "candidatures/entretien";

function setup(options: InterviewApiOptions = {}) {
  const sockets = createFakeSocketServer();
  const interviews = interviewApi(options);
  server.use(...interviews.handlers);
  const routes = applicationsManifest.routes.map((route) =>
    route.path === ROUTE
      ? { path: route.path, element: <FreeInterviewPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, "/candidatures/entretien", {
    applications: [applicationOut({ id: "a1" })],
  });
  return { ...view, sockets, interviews };
}

const START = "Start the interview";

describe("FreeInterviewPage", () => {
  beforeEach(() => useSessionStore.getState().reset("iv-s-new"));

  it("is the free interview: no application, a choice between an offer and a job title", async () => {
    setup({ postings: [postingOut({ id: "p1", company: "Acme", title: "Data engineer" })] });
    expect(
      await screen.findByRole("heading", { level: 1, name: "Open mock interview" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to applications" })).toHaveAttribute(
      "href",
      "/candidatures",
    );
    const target = await screen.findByRole("group", { name: "What is the interview about?" });
    expect(within(target).getByRole("radio", { name: "An analyzed posting" })).toBeChecked();
    const posting = screen.getByRole("combobox", { name: "Posting" });
    expect(within(posting).getByRole("option", { name: "Acme, Data engineer" })).toBeVisible();
  });

  it("starts an interview on an offer: posting_id, no role", async () => {
    const view = setup({
      postings: [postingOut({ id: "p1", company: "Acme", title: "Data engineer" })],
    });
    await view.user.selectOptions(await screen.findByRole("combobox", { name: "Posting" }), "p1");
    await view.user.click(screen.getByRole("radio", { name: "Technical" }));
    await view.user.click(screen.getByRole("button", { name: START }));
    await waitFor(() => expect(view.interviews.state.starts).toHaveLength(1));
    expect(view.interviews.state.starts[0]).toEqual({
      applicationId: null,
      body: { mode: "technical", duration_min: 30, language: "en", posting_id: "p1" },
    });
    await openStream(view.sockets, "iv-s-new");
  });

  it("starts an interview on a job title: role, no posting_id", async () => {
    const view = setup({ postings: [postingOut({ id: "p1" })] });
    await view.user.click(await screen.findByRole("radio", { name: "A job title" }));
    await view.user.type(
      screen.getByRole("textbox", { name: /^Job title/ }),
      "  Data engineer  ",
    );
    await view.user.click(screen.getByRole("button", { name: START }));
    await waitFor(() => expect(view.interviews.state.starts).toHaveLength(1));
    expect(view.interviews.state.starts[0]?.body).toEqual({
      mode: "mixed",
      duration_min: 30,
      language: "en",
      role: "Data engineer",
    });
  });

  it("goes straight to the job title when there is no analysed offer", async () => {
    setup({ postings: [postingOut({ id: "p2", status: "analyzing" })] });
    expect(await screen.findByText(/You don't have an analyzed posting yet/)).toBeVisible();
    expect(screen.queryByRole("combobox", { name: "Posting" })).toBeNull();
    expect(screen.getByRole("textbox", { name: /^Job title/ })).toBeVisible();
  });

  it("asks for an offer or a title and sends nothing when both are empty", async () => {
    const view = setup({ postings: [] });
    await view.user.click(await screen.findByRole("button", { name: START }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Choose a posting or enter a job title.",
    );
    expect(view.interviews.state.starts).toHaveLength(0);
  });

  it("lists only the interviews that have no application", async () => {
    const view = setup({
      postings: [],
      interviews: [
        interviewOut({ id: "f1", application_id: null, role: "Data engineer" }),
        interviewOut({ id: "k1", application_id: "a1" }),
      ],
    });
    const list = await screen.findByRole("list", { name: "Past interviews" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    expect(within(list).getByText("Role: Data engineer")).toBeVisible();
    await view.user.click(within(list).getByRole("button"));
    expect(await screen.findByRole("heading", { name: "Interview debrief" })).toBeVisible();
  });

  it("names a free interview on an offer by the offer", async () => {
    setup({
      postings: [postingOut({ id: "p1", company: "Acme", title: "Data engineer" })],
      interviews: [interviewOut({ id: "f2", application_id: null, posting_id: "p1", role: null })],
    });
    const list = await screen.findByRole("list", { name: "Past interviews" });
    expect(await within(list).findByText("Posting: Acme, Data engineer")).toBeVisible();
  });

  it("asks the first question of a free interview like any other", async () => {
    const view = setup({ postings: [] });
    await view.user.type(
      await screen.findByRole("textbox", { name: /^Job title/ }),
      "Data engineer",
    );
    await view.user.click(screen.getByRole("button", { name: START }));
    const stream = await openStream(view.sockets, "iv-s-new");
    const e = councilEvents("iv-s-new");
    stream.push(
      e.message("interviewer-q1", "Tell me about yourself.", "interviewer"),
      e.interrupt("interview_answer", "q1", {
        question: "Tell me about yourself.",
        options: [{ value: "stop", label: "End the interview" }],
      }),
    );
    expect(await screen.findByRole("region", { name: "Question 1 of 7" })).toBeVisible();
  });
});
