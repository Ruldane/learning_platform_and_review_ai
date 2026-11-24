import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { expectCoherentOutline } from "@/test/headingOutline";
import { apiError, recordPosts } from "@/test/councilHarness";
import { interviewOut } from "@/test/interviewApi";
import { ask, SESSION, setup, startInterview } from "./interviewTestkit";

describe("InterviewPage settings", () => {
  beforeEach(() => useSessionStore.getState().reset(SESSION));

  it("introduces the interview with the application and offers the interview modes including salary negotiation", async () => {
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: "Mock interview" })).toBeVisible();
    expect(await screen.findByText("Acme, Data engineer")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the application" })).toHaveAttribute(
      "href",
      "/candidatures/a1",
    );
    const mode = await screen.findByRole("group", { name: "Format" });
    expect(
      within(mode)
        .getAllByRole("radio")
        .map((radio) => radio.getAttribute("value")),
    ).toEqual(["behavioral", "technical", "case", "mixed", "salary"]);
    const duration = screen.getByRole("group", { name: "Duration" });
    expect(within(duration).getByRole("radio", { name: "15 minutes" })).toHaveAccessibleDescription(
      "4 main questions",
    );
    expect(within(duration).getByRole("radio", { name: "45 minutes" })).toHaveAccessibleDescription(
      "10 main questions",
    );
    const language = screen.getByRole("group", { name: "Question language" });
    expect(within(language).getByRole("radio", { name: "English" })).toBeChecked();
    expect(await screen.findByText("No interviews yet.")).toBeVisible();
  });

  it("starts the interview with the chosen settings, on this application", async () => {
    const view = setup();
    await view.user.click(await screen.findByRole("radio", { name: "Technical" }));
    await view.user.click(screen.getByRole("radio", { name: "45 minutes" }));
    await view.user.click(screen.getByRole("radio", { name: "French" }));
    await view.user.click(screen.getByRole("button", { name: "Start the interview" }));
    await waitFor(() => expect(view.interviews.state.starts).toHaveLength(1));
    expect(view.interviews.state.starts[0]).toEqual({
      applicationId: "a1",
      body: { mode: "technical", duration_min: 45, language: "fr" },
    });
    await openStream(view.sockets, SESSION);
    expect(screen.queryByRole("button", { name: "Start the interview" })).toBeNull();
  });

  it("says the profile is missing and links to it", async () => {
    const view = setup({
      start: () =>
        HttpResponse.json(apiError("profile_required", "Profile required."), { status: 409 }),
    });
    await view.user.click(await screen.findByRole("button", { name: "Start the interview" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No validated master profile");
    expect(screen.getByRole("link", { name: "Open my profile" })).toHaveAttribute(
      "href",
      "/carriere/profil",
    );
    expect(screen.getByRole("button", { name: "Start the interview" })).toBeEnabled();
  });

  it("takes up the interview already open instead of failing (409)", async () => {
    const view = setup({
      interviews: [],
      start: () =>
        HttpResponse.json(
          apiError("interview_in_progress", "Already in progress.", { interview_id: "iv9" }),
          { status: 409 },
        ),
    });
    const start = await screen.findByRole("button", { name: "Start the interview" });
    view.interviews.interviews.push(
      interviewOut({
        id: "iv9",
        status: "running",
        session_id: "iv-s9",
        exchanges: [],
        debrief: null,
      }),
    );
    await view.user.click(start);
    await openStream(view.sockets, "iv-s9");
    expect(
      await screen.findByText("An interview was already in progress: you're picking it up here."),
    ).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("says when the interview taken up belongs to another application, with a link to it", async () => {
    const view = setup({
      start: () =>
        HttpResponse.json(
          apiError("interview_in_progress", "Already in progress.", { interview_id: "iv9" }),
          { status: 409 },
        ),
    });
    const start = await screen.findByRole("button", { name: "Start the interview" });
    view.interviews.interviews.push(
      interviewOut({
        id: "iv9",
        application_id: "a2",
        status: "running",
        session_id: "iv-s9",
        exchanges: [],
        debrief: null,
      }),
    );
    await view.user.click(start);
    await openStream(view.sockets, "iv-s9");
    expect(
      await screen.findByText("An interview is already in progress on another application."),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Open that application" })).toHaveAttribute(
      "href",
      "/candidatures/a2/entretien",
    );
  });

  it("says the agents are unavailable and keeps the settings", async () => {
    const view = setup({
      start: () =>
        HttpResponse.json(apiError("engine_unavailable", "Unavailable."), { status: 503 }),
    });
    await view.user.click(await screen.findByRole("radio", { name: "Case study" }));
    await view.user.click(screen.getByRole("button", { name: "Start the interview" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The agents aren't available right now",
    );
    expect(screen.getByRole("radio", { name: "Case study" })).toBeChecked();
  });

  it("says when the application does not exist", async () => {
    setup({}, "/candidatures/zz/entretien");
    expect(await screen.findByText("This application no longer exists.")).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Application not found" })).toBeVisible();
  });
});

describe("InterviewPage written interview", () => {
  beforeEach(() => useSessionStore.getState().reset(SESSION));

  it("shows one question at a time with its number, focus on the answer, and announces it", async () => {
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Parle-moi d'un projet récent."));
    const card = await screen.findByRole("region", { name: "Question 1 of 7" });
    expect(within(card).getByRole("textbox", { name: "Your written answer" })).toHaveFocus();
    expect(screen.getAllByText("Parle-moi d'un projet récent.").length).toBeGreaterThan(0);
    await waitFor(() =>
      expect(
        screen
          .getAllByRole("status")
          .some((zone) => zone.textContent === "Question 1 of 7. Parle-moi d'un projet récent."),
      ).toBe(true),
    );
  });

  it("nests the question title under the page title (one h1, then h2)", async () => {
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Parle-moi d'un projet récent."));
    await screen.findByRole("region", { name: "Question 1 of 7" });
    expectCoherentOutline();
    expect(screen.getByRole("heading", { level: 2, name: "Question 1 of 7" })).toBeVisible();
  });

  it("sends the answer as {answers: {answer}}, folds the card and shows the next question", async () => {
    const resumes = recordPosts(`/sessions/${SESSION}/resume`, 200, sessionOut(SESSION, "running"));
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première question ?"));
    const first = await screen.findByRole("region", { name: "Question 1 of 7" });
    await view.user.type(within(first).getByRole("textbox"), "Voici ma réponse");
    await view.user.click(within(first).getByRole("button", { name: "Answer" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({
      interrupt_id: "q1",
      value: { answers: { answer: "Voici ma réponse" } },
    });
    await waitFor(() => expect(within(first).queryByRole("textbox")).toBeNull());
    expect(within(first).getByText("Answer sent")).toBeVisible();
    expect(within(first).getByText("Voici ma réponse")).toBeVisible();

    stream.push(...ask(e, 2, "q2", "Seconde question ?"));
    const second = await screen.findByRole("region", { name: "Question 2 of 7" });
    expect(within(second).getByRole("textbox")).toHaveFocus();
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
  });

  it("names a follow-up as such, with the number of its question", async () => {
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(
      ...ask(e, 1, "q1", "Première question ?"),
      e.message("interviewer-q1-relance", "Peux-tu préciser ?", "interviewer"),
      e.interrupt("interview_answer", "q1r", {
        question: "Peux-tu préciser ?",
        options: [{ value: "stop", label: "End the interview" }],
        fields: [{ id: "answer", label: "Your answer", required: true, max_length: 4000 }],
      }),
    );
    expect(
      await screen.findByRole("region", { name: "Follow-up on question 1 of 7" }),
    ).toBeVisible();
  });

  it("keeps the same question number when the server asks it again after an unreadable answer", async () => {
    recordPosts(`/sessions/${SESSION}/resume`, 200, sessionOut(SESSION, "running"));
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première question ?"));
    const first = await screen.findByRole("region", { name: "Question 1 of 7" });
    await view.user.type(within(first).getByRole("textbox"), "   ?");
    await view.user.click(within(first).getByRole("button", { name: "Answer" }));
    await waitFor(() => expect(within(first).queryByRole("textbox")).toBeNull());
    stream.push(
      e.interrupt("interview_answer", "q1b", {
        question: "Première question ?",
        options: [{ value: "stop", label: "End the interview" }],
        fields: [{ id: "answer", label: "Your answer", required: true, max_length: 4000 }],
      }),
    );
    await waitFor(() =>
      expect(screen.getAllByRole("region", { name: "Question 1 of 7" })).toHaveLength(2),
    );
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
  });

  it("counts the questions of a shorter interview: 15 minutes make 4", async () => {
    const view = setup();
    await view.user.click(await screen.findByRole("radio", { name: "15 minutes" }));
    await view.user.click(screen.getByRole("button", { name: "Start the interview" }));
    const stream = await openStream(view.sockets, SESSION);
    stream.push(...ask(councilEvents(SESSION), 3, "q3", "Troisième ?"));
    expect(await screen.findByRole("region", { name: "Question 3 of 4" })).toBeVisible();
  });

  it("ends the interview by sending the stop value", async () => {
    const resumes = recordPosts(`/sessions/${SESSION}/resume`, 200, sessionOut(SESSION, "running"));
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première question ?"));
    await view.user.click(await screen.findByRole("button", { name: "End the interview" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "q1", value: "stop" }]));
    expect(await screen.findByText("You ended the interview.")).toBeVisible();
  });

  it("says the debrief is being written after ending the interview", async () => {
    recordPosts(`/sessions/${SESSION}/resume`, 200, sessionOut(SESSION, "running"));
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première ?"));
    await view.user.click(await screen.findByRole("button", { name: "End the interview" }));
    expect(await screen.findByText(/the debrief is being written/)).toBeVisible();
  });

  it("says it after the answer to the last question, and takes it back if a follow-up comes", async () => {
    recordPosts(`/sessions/${SESSION}/resume`, 200, sessionOut(SESSION, "running"));
    const view = setup();
    await view.user.click(await screen.findByRole("radio", { name: "15 minutes" }));
    await view.user.click(screen.getByRole("button", { name: "Start the interview" }));
    const stream = await openStream(view.sockets, SESSION);
    const e = councilEvents(SESSION);
    stream.push(...ask(e, 3, "q3", "Troisième ?"));
    const third = await screen.findByRole("region", { name: "Question 3 of 4" });
    await view.user.type(within(third).getByRole("textbox"), "Réponse");
    await view.user.click(within(third).getByRole("button", { name: "Answer" }));
    expect(screen.queryByText(/the debrief is being written/)).toBeNull();
    stream.push(...ask(e, 4, "q4", "Dernière ?"));
    const last = await screen.findByRole("region", { name: "Question 4 of 4" });
    await view.user.type(within(last).getByRole("textbox"), "Fin");
    await view.user.click(within(last).getByRole("button", { name: "Answer" }));
    expect(await screen.findByText(/the debrief is being written/)).toBeVisible();
    stream.push(
      e.message("interviewer-q4-relance", "Précise ?", "interviewer"),
      e.interrupt("interview_answer", "q4r", { question: "Précise ?", options: [] }),
    );
    await screen.findByRole("region", { name: "Follow-up on question 4 of 4" });
    expect(screen.queryByText(/the debrief is being written/)).toBeNull();
  });
});
