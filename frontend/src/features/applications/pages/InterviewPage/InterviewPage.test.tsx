import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { openStream } from "@/test/applicationsHarness";
import { sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { apiError, recordPosts } from "@/test/councilHarness";
import { interviewOut } from "@/test/interviewApi";
import { ask, SESSION, setup, startInterview } from "./interviewTestkit";

describe("InterviewPage, réglages", () => {
  beforeEach(() => useSessionStore.getState().reset(SESSION));

  it("introduces the interview with the application and offers the four settings", async () => {
    setup();
    expect(await screen.findByRole("heading", { level: 1, name: "Entretien blanc" })).toBeVisible();
    expect(await screen.findByText("Acme, Data engineer")).toBeVisible();
    expect(screen.getByRole("link", { name: "Retour à la fiche" })).toHaveAttribute(
      "href",
      "/candidatures/a1",
    );
    const mode = await screen.findByRole("group", { name: "Formule" });
    expect(
      within(mode)
        .getAllByRole("radio")
        .map((radio) => radio.getAttribute("value")),
    ).toEqual(["behavioral", "technical", "case", "mixed"]);
    const duration = screen.getByRole("group", { name: "Durée" });
    expect(within(duration).getByRole("radio", { name: "15 minutes" })).toHaveAccessibleDescription(
      "4 questions principales",
    );
    expect(within(duration).getByRole("radio", { name: "45 minutes" })).toHaveAccessibleDescription(
      "10 questions principales",
    );
    const language = screen.getByRole("group", { name: "Langue des questions" });
    expect(within(language).getByRole("radio", { name: "Français" })).toBeChecked();
    expect(await screen.findByText("Aucun entretien pour l'instant.")).toBeVisible();
  });

  it("starts the interview with the chosen settings, on this application", async () => {
    const view = setup();
    await view.user.click(await screen.findByRole("radio", { name: "Technique" }));
    await view.user.click(screen.getByRole("radio", { name: "45 minutes" }));
    await view.user.click(screen.getByRole("radio", { name: "Anglais" }));
    await view.user.click(screen.getByRole("button", { name: "Commencer l'entretien" }));
    await waitFor(() => expect(view.interviews.state.starts).toHaveLength(1));
    expect(view.interviews.state.starts[0]).toEqual({
      applicationId: "a1",
      body: { mode: "technical", duration_min: 45, language: "en" },
    });
    await openStream(view.sockets, SESSION);
    expect(screen.queryByRole("button", { name: "Commencer l'entretien" })).toBeNull();
  });

  it("says the profile is missing and links to it", async () => {
    const view = setup({
      start: () =>
        HttpResponse.json(apiError("profile_required", "Profil requis."), { status: 409 }),
    });
    await view.user.click(await screen.findByRole("button", { name: "Commencer l'entretien" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Aucun profil maître validé");
    expect(screen.getByRole("link", { name: "Ouvrir mon profil" })).toHaveAttribute(
      "href",
      "/carriere/profil",
    );
    expect(screen.getByRole("button", { name: "Commencer l'entretien" })).toBeEnabled();
  });

  it("takes up the interview already open instead of failing (409)", async () => {
    const view = setup({
      interviews: [],
      start: () =>
        HttpResponse.json(
          apiError("interview_in_progress", "Déjà en cours.", { interview_id: "iv9" }),
          { status: 409 },
        ),
    });
    const start = await screen.findByRole("button", { name: "Commencer l'entretien" });
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
      await screen.findByText("Un entretien était déjà en cours : tu le reprends ici."),
    ).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("says the agents are unavailable and keeps the settings", async () => {
    const view = setup({
      start: () =>
        HttpResponse.json(apiError("engine_unavailable", "Indisponible."), { status: 503 }),
    });
    await view.user.click(await screen.findByRole("radio", { name: "Étude de cas" }));
    await view.user.click(screen.getByRole("button", { name: "Commencer l'entretien" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Les agents ne sont pas disponibles",
    );
    expect(screen.getByRole("radio", { name: "Étude de cas" })).toBeChecked();
  });

  it("says when the application does not exist", async () => {
    setup({}, "/candidatures/zz/entretien");
    expect(await screen.findByText("Cette candidature n'existe plus.")).toBeVisible();
  });
});

describe("InterviewPage, échange écrit", () => {
  beforeEach(() => useSessionStore.getState().reset(SESSION));

  it("shows one question at a time with its number, focus on the answer, and announces it", async () => {
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Parle-moi d'un projet récent."));
    const card = await screen.findByRole("region", { name: "Question 1 sur 7" });
    expect(within(card).getByRole("textbox", { name: "Ta réponse écrite" })).toHaveFocus();
    expect(screen.getAllByText("Parle-moi d'un projet récent.").length).toBeGreaterThan(0);
    await waitFor(() =>
      expect(
        screen
          .getAllByRole("status")
          .some((zone) => zone.textContent === "Question 1 sur 7. Parle-moi d'un projet récent."),
      ).toBe(true),
    );
  });

  it("sends the answer as {answers: {answer}}, folds the card and shows the next question", async () => {
    const resumes = recordPosts(`/sessions/${SESSION}/resume`, 200, sessionOut(SESSION, "running"));
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première question ?"));
    const first = await screen.findByRole("region", { name: "Question 1 sur 7" });
    await view.user.type(within(first).getByRole("textbox"), "Voici ma réponse");
    await view.user.click(within(first).getByRole("button", { name: "Répondre" }));
    await waitFor(() => expect(resumes).toHaveLength(1));
    expect(resumes[0]).toEqual({
      interrupt_id: "q1",
      value: { answers: { answer: "Voici ma réponse" } },
    });
    await waitFor(() => expect(within(first).queryByRole("textbox")).toBeNull());
    expect(within(first).getByText("Réponse envoyée")).toBeVisible();
    expect(within(first).getByText("Voici ma réponse")).toBeVisible();

    stream.push(...ask(e, 2, "q2", "Seconde question ?"));
    const second = await screen.findByRole("region", { name: "Question 2 sur 7" });
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
        options: [{ value: "stop", label: "Terminer l'entretien" }],
        fields: [{ id: "answer", label: "Ta réponse", required: true, max_length: 4000 }],
      }),
    );
    expect(
      await screen.findByRole("region", { name: "Relance sur la question 1 sur 7" }),
    ).toBeVisible();
  });

  it("keeps the same question number when the server asks it again after an unreadable answer", async () => {
    recordPosts(`/sessions/${SESSION}/resume`, 200, sessionOut(SESSION, "running"));
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première question ?"));
    const first = await screen.findByRole("region", { name: "Question 1 sur 7" });
    await view.user.type(within(first).getByRole("textbox"), "   ?");
    await view.user.click(within(first).getByRole("button", { name: "Répondre" }));
    await waitFor(() => expect(within(first).queryByRole("textbox")).toBeNull());
    stream.push(
      e.interrupt("interview_answer", "q1b", {
        question: "Première question ?",
        options: [{ value: "stop", label: "Terminer l'entretien" }],
        fields: [{ id: "answer", label: "Ta réponse", required: true, max_length: 4000 }],
      }),
    );
    await waitFor(() =>
      expect(screen.getAllByRole("region", { name: "Question 1 sur 7" })).toHaveLength(2),
    );
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
  });

  it("counts the questions of a shorter interview: 15 minutes make 4", async () => {
    const view = setup();
    await view.user.click(await screen.findByRole("radio", { name: "15 minutes" }));
    await view.user.click(screen.getByRole("button", { name: "Commencer l'entretien" }));
    const stream = await openStream(view.sockets, SESSION);
    stream.push(...ask(councilEvents(SESSION), 3, "q3", "Troisième ?"));
    expect(await screen.findByRole("region", { name: "Question 3 sur 4" })).toBeVisible();
  });

  it("ends the interview with « Terminer l'entretien », which sends the option value", async () => {
    const resumes = recordPosts(`/sessions/${SESSION}/resume`, 200, sessionOut(SESSION, "running"));
    const view = setup();
    const { stream, e } = await startInterview(view);
    stream.push(...ask(e, 1, "q1", "Première question ?"));
    await view.user.click(await screen.findByRole("button", { name: "Terminer l'entretien" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "q1", value: "stop" }]));
    expect(await screen.findByText("Tu as terminé l'entretien.")).toBeVisible();
  });
});
