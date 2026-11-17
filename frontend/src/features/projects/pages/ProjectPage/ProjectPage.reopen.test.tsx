import { focusManager } from "@tanstack/react-query";
import { act, screen, waitFor } from "@testing-library/react";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { councilEvents } from "@/test/councilEvents";
import { apiError } from "@/test/councilHarness";
import { briefOut, evaluationOut, fourDrafts, projectOut, submissionOut } from "@/test/projectsApi";
import { openStream, renderProjects } from "@/test/projectsHarness";
import { PortfolioPage } from "../PortfolioPage";
import { ProjectPage } from "./ProjectPage";

const setup = (api: Parameters<typeof renderProjects>[1] = {}) =>
  renderProjects(
    (createSocket) => ({
      portfolio: <PortfolioPage />,
      project: <ProjectPage createSocket={createSocket} />,
    }),
    api,
    "/competences/portfolio/p1",
  );

const validated = (over: Record<string, unknown> = {}) =>
  projectOut("p1", {
    status: "validated",
    validated_at: "2026-11-16T12:00:00Z",
    evaluation: evaluationOut({ verdict: "validated" }),
    ...over,
  });

const regenerate = () => screen.findByRole("button", { name: "Régénérer les brouillons" });

describe("ProjectPage : le formulaire « à reprendre »", () => {
  it("to-redo form prefilled with last submission", async () => {
    const project = projectOut("p1", {
      status: "to_redo",
      evaluation: evaluationOut(),
      submissions: [
        submissionOut({
          repo_url: "https://example.org/camille/ventes-2",
          description: "Deuxième rendu.",
        }),
        submissionOut({
          repo_url: "https://example.org/camille/ventes-1",
          description: "Premier.",
        }),
      ],
    });
    setup({ projects: [project] });
    expect(await screen.findByLabelText("Lien du dépôt")).toHaveValue(
      "https://example.org/camille/ventes-2",
    );
    expect(screen.getByLabelText("Description")).toHaveValue("Deuxième rendu.");
  });

  it("says that the screenshots of the last submission are not carried over", async () => {
    const project = projectOut("p1", {
      status: "to_redo",
      evaluation: evaluationOut(),
      submissions: [submissionOut({ screenshots: 2 })],
    });
    setup({ projects: [project] });
    expect(
      await screen.findByText("Les captures du dernier rendu ne sont pas reprises : ajoute-les."),
    ).toBeVisible();
  });

  it("leaves the form empty on a first submission", async () => {
    setup({ projects: [projectOut("p1")] });
    expect(await screen.findByLabelText("Description")).toHaveValue("");
    expect(screen.getByLabelText("Lien du dépôt")).toHaveValue("");
    expect(screen.queryByText(/ne sont pas reprises/)).toBeNull();
  });

  it("sends the prefilled values as they are when the person only submits", async () => {
    const project = projectOut("p1", {
      status: "to_redo",
      evaluation: evaluationOut(),
      submissions: [submissionOut({ repo_url: null, description: "Une requête SQL." })],
    });
    const { user, state } = setup({ projects: [project] });
    await screen.findByDisplayValue("Une requête SQL.");
    await user.click(await screen.findByRole("button", { name: "Rendre le projet" }));
    await screen.findByRole("heading", { name: "Évaluation en cours" });
    expect(state.submits).toHaveLength(1);
  });
});

describe("ProjectPage : régénérer les brouillons", () => {
  it("regenerate drafts button only when validated without drafts", async () => {
    setup({ projects: [validated()] });
    expect(await regenerate()).toBeVisible();
    expect(screen.getByText("Aucun brouillon n'a été écrit pour ce projet.")).toBeVisible();
  });

  it("does not offer it when the drafts exist", async () => {
    setup({ projects: [validated({ drafts: fourDrafts() })] });
    await screen.findByLabelText("Ligne de CV");
    expect(screen.queryByRole("button", { name: "Régénérer les brouillons" })).toBeNull();
  });

  it.each([
    ["todo", {}],
    ["to_redo", { evaluation: evaluationOut() }],
    ["brief_failed", { brief: null }],
  ])("does not offer it for a project that is %s", async (status, over) => {
    setup({ projects: [projectOut("p1", { status, ...over })] });
    await screen.findByRole("heading", { level: 1, name: "Pipeline de ventes" });
    expect(screen.queryByRole("button", { name: "Régénérer les brouillons" })).toBeNull();
  });

  it("starts the writing once, follows it, then shows the drafts", async () => {
    const { user, state, settle, sockets } = setup({ projects: [validated()] });
    await user.dblClick(await regenerate());
    const writing = await screen.findByRole("heading", { name: "Brouillons en cours d'écriture" });
    expect(writing).toBeVisible();
    // Le bouton cliqué a disparu : le titre du suivi prend le focus, jamais `body`.
    await waitFor(() => expect(writing).toHaveFocus());
    expect(state.regenerations).toEqual(["p1"]);
    expect(screen.queryByRole("button", { name: "Régénérer les brouillons" })).toBeNull();

    const stream = await openStream(sockets, "sess-drafts-p1");
    const events = councilEvents("sess-drafts-p1");
    stream.push(events.message("m1", "J'écris ta ligne de CV.", "practitioner"));
    expect(await screen.findByText("J'écris ta ligne de CV.")).toBeVisible();

    settle("p1", { drafts: fourDrafts() });
    stream.push(events.completed());
    expect(await screen.findByLabelText("Ligne de CV")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Régénérer les brouillons" })).toBeNull();
    // Ni le bouton ni le suivi n'existent plus : le titre de la section a le focus, pas `body`.
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Tes brouillons" })).toHaveFocus(),
    );
  });

  it("offers the button again, with a message, when the writing ends without drafts", async () => {
    const { user, sockets } = setup({
      projects: [validated()],
      draftsSessionId: "sess-drafts-bad",
    });
    await user.click(await regenerate());
    const stream = await openStream(sockets, "sess-drafts-bad");
    stream.push(councilEvents("sess-drafts-bad").failed());
    expect(await screen.findByText(/n'ont pas pu être écrits/)).toBeVisible();
    // Le suivi a disparu : le bouton reprend le focus.
    await waitFor(async () => expect(await regenerate()).toHaveFocus());
  });

  it("says so when the writing ends without drafts although it did not fail", async () => {
    const { user, sockets } = setup({
      projects: [validated()],
      draftsSessionId: "sess-drafts-empty",
    });
    await user.click(await regenerate());
    const stream = await openStream(sockets, "sess-drafts-empty");
    stream.push(councilEvents("sess-drafts-empty").completed());
    expect(await screen.findByText(/n'ont pas pu être écrits/)).toBeVisible();
    expect(await regenerate()).toBeVisible();
  });

  it("explains a 409 review_in_progress that does not name the running session", async () => {
    const { user } = setup({
      projects: [validated()],
      draftsReply: () =>
        HttpResponse.json(apiError("review_in_progress", "Déjà en cours."), { status: 409 }),
    });
    await user.click(await regenerate());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Leur écriture est déjà en cours, mais on ne retrouve pas son suivi",
    );
    expect(screen.queryByText(/évaluation/)).toBeNull();
    expect(await regenerate()).toBeVisible();
  });

  it("has its own text for a 409 project_not_validated", async () => {
    const { user } = setup({
      projects: [validated()],
      draftsReply: () =>
        HttpResponse.json(apiError("project_not_validated", "Pas validé."), { status: 409 }),
    });
    await user.click(await regenerate());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ce projet n'est plus validé : la page se relit.",
    );
    expect(screen.queryByText("Seul un projet validé peut entrer dans ton profil.")).toBeNull();
  });

  it("reads the project again when the server says the drafts already exist (409)", async () => {
    const { user, state, settle } = setup({ projects: [validated()] });
    const button = await regenerate();
    settle("p1", { drafts: fourDrafts() });
    await user.click(button);
    expect(state.regenerations).toEqual(["p1"]);
    expect(await screen.findByLabelText("Ligne de CV")).toBeVisible();
  });

  it("shows a refusal that is not a conflict, and keeps the button", async () => {
    const { user } = setup({
      projects: [validated()],
      draftsReply: () =>
        HttpResponse.json(apiError("internal_error", "Panne du serveur."), { status: 500 }),
    });
    await user.click(await regenerate());
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    expect(await regenerate()).toBeVisible();
  });
});

describe("ProjectPage : le focus de « Réessayer l'énoncé » ne sert qu'une fois", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("retry flag resets after success", async () => {
    const failed = projectOut("p1", { status: "brief_failed", brief: null });
    const { user, settle } = setup({ projects: [failed] });
    await user.click(await screen.findByRole("button", { name: "Réessayer l'énoncé" }));
    expect(
      await screen.findByRole("heading", { name: "Énoncé en cours d'écriture" }),
    ).toHaveFocus();

    // L'énoncé est écrit : la page le montre, et le focus demandé est consommé.
    settle("p1", { status: "todo", brief: briefOut(), session_id: null });
    await act(() => vi.advanceTimersByTimeAsync(5_500));
    expect(await screen.findByText("Durée estimée : 6 h")).toBeVisible();

    // Un autre onglet relance l'énoncé : la page se relit au retour de l'onglet, sans reprendre le
    // focus.
    settle("p1", { status: "brief_pending", brief: null, session_id: "sess-b2" });
    await act(async () => {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
      await vi.advanceTimersByTimeAsync(100);
    });
    const title = await screen.findByRole("heading", { name: "Énoncé en cours d'écriture" });
    expect(title).not.toHaveFocus();
  });
});
