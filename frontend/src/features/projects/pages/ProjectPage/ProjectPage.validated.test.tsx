import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { apiError } from "@/test/councilHarness";
import {
  criterionOut,
  draftOut,
  evaluationOut,
  fourDrafts,
  projectOut,
  submissionOut,
} from "@/test/projectsApi";
import { renderProjects } from "@/test/projectsHarness";
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
    evaluation: evaluationOut({
      verdict: "validated",
      feedback: "Tout est atteint.",
      results: [criterionOut(1, true), criterionOut(2, true), criterionOut(3, true)],
    }),
    submissions: [submissionOut({ screenshots: 2 })],
    drafts: fourDrafts(),
    ...over,
  });

const addButton = () => screen.findByRole("button", { name: "Ajouter au profil maître" });

describe("ProjectPage : un projet validé", () => {
  it("shows the validation, the evaluation, the drafts and the entry, and links to the skills map", async () => {
    const { user, router } = setup({ projects: [validated()] });
    expect(await screen.findByRole("heading", { name: "Projet validé" })).toBeVisible();
    expect(screen.getByText("Validé le 16 novembre 2026.")).toBeVisible();
    expect(screen.getByText("Tout est atteint.")).toBeVisible();
    expect(screen.getAllByText("Atteint").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByLabelText("Ligne de CV")).toHaveValue("Texte du brouillon cv_line.");
    expect(screen.getByLabelText("Post LinkedIn")).toHaveValue("Texte du brouillon linkedin_post.");
    expect(screen.getByLabelText("Plan de README")).toHaveValue("Texte du brouillon readme_plan.");
    expect(screen.getByLabelText("Nom du projet")).toHaveValue("Pipeline de ventes");
    expect(screen.getByLabelText("Réalisations")).toHaveValue(
      "Requêtes SQL optimisées\nTest du total",
    );
    expect(screen.getByText("Rien n'entre dans ton profil sans ton accord.")).toBeVisible();
    expect(screen.getByText("Captures non lues par le Praticien.")).toBeVisible();
    expect(screen.queryByRole("form", { name: "Rendre ton projet" })).toBeNull();

    await user.click(screen.getByRole("link", { name: "Voir la carte des compétences" }));
    expect(router.state.location.pathname).toBe("/competences");
  });

  it("does not claim the screenshots were unread when the last submission had none", async () => {
    setup({ projects: [validated({ submissions: [submissionOut({ screenshots: 0 })] })] });
    await screen.findByText("Tout est atteint.");
    expect(screen.queryByText("Captures non lues par le Praticien.")).toBeNull();
  });

  it("takes the screenshot mention from the latest submission, not an older one", async () => {
    setup({
      projects: [
        validated({
          submissions: [
            submissionOut({ at: "2026-11-16T12:00:00Z", screenshots: 0 }),
            submissionOut({ at: "2026-11-15T12:00:00Z", screenshots: 3 }),
          ],
        }),
      ],
    });
    await screen.findByText("Tout est atteint.");
    expect(screen.queryByText("Captures non lues par le Praticien.")).toBeNull();
  });
});

describe("ProjectPage : les brouillons", () => {
  const flagged = (flags: string[]) =>
    fourDrafts({
      cv_line: { status: "to_check", flags, content: "Déployé sur Kubernetes." },
    });

  it("warns about a draft to check, and sends the retouched text", async () => {
    const { user, state } = setup({
      projects: [validated({ drafts: flagged(["Kubernetes"]) })],
      recheckFlags: [],
    });
    expect(
      await screen.findByText(/absent de ton profil et de ton rendu : Kubernetes/),
    ).toBeVisible();
    const field = screen.getByLabelText("Ligne de CV");
    await user.clear(field);
    await user.type(field, "Déployé avec Docker.");
    await user.click(
      within(field.closest("article")!).getByRole("button", { name: "Enregistrer" }),
    );
    await waitFor(() =>
      expect(state.patches).toEqual([
        { id: "p1", kind: "cv_line", body: { content: "Déployé avec Docker." } },
      ]),
    );
    await waitFor(() =>
      expect(screen.queryByText(/absent de ton profil et de ton rendu : Kubernetes/)).toBeNull(),
    );
    expect(screen.getByLabelText("Ligne de CV")).toHaveValue("Déployé avec Docker.");
    expect(screen.getByText("Retouché par toi")).toBeVisible();
  });

  it("keeps the warning when the server still finds a term to check", async () => {
    const { user } = setup({
      projects: [validated({ drafts: flagged(["Kubernetes"]) })],
      recheckFlags: ["Kubernetes"],
    });
    const field = await screen.findByLabelText("Ligne de CV");
    await user.type(field, " Merci.");
    await user.click(
      within(field.closest("article")!).getByRole("button", { name: "Enregistrer" }),
    );
    await screen.findByText("Retouché par toi");
    expect(screen.getByText(/absent de ton profil et de ton rendu : Kubernetes/)).toBeVisible();
  });

  it("copies the text on screen and confirms", async () => {
    const { user } = setup({ projects: [validated()] });
    const field = await screen.findByLabelText("Post LinkedIn");
    await user.type(field, " Merci !");
    await user.click(within(field.closest("article")!).getByRole("button", { name: "Copier" }));
    expect(await screen.findByText("Brouillon copié.")).toBeVisible();
    expect(await navigator.clipboard.readText()).toBe("Texte du brouillon linkedin_post. Merci !");
  });

  it("does not say the draft was copied when the clipboard is missing", async () => {
    const { user } = setup({ projects: [validated()] });
    const field = await screen.findByLabelText("Post LinkedIn");
    const original = Object.getOwnPropertyDescriptor(navigator, "clipboard");
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    try {
      await user.click(within(field.closest("article")!).getByRole("button", { name: "Copier" }));
      expect(await screen.findByText(/Copie impossible/)).toBeVisible();
      expect(screen.queryByText("Brouillon copié.")).toBeNull();
    } finally {
      if (original) Object.defineProperty(navigator, "clipboard", original);
    }
  });

  it("does not say the draft was copied when the browser refuses", async () => {
    const { user } = setup({ projects: [validated()] });
    const field = await screen.findByLabelText("Post LinkedIn");
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("denied"));
    await user.click(within(field.closest("article")!).getByRole("button", { name: "Copier" }));
    expect(await screen.findByText(/Copie impossible/)).toBeVisible();
    expect(screen.queryByText("Brouillon copié.")).toBeNull();
  });
});

describe("ProjectPage : l'ajout au profil maître", () => {
  it("adds nothing on its own, then replaces the button by « Ajouté au profil (version 4) »", async () => {
    const { user, state } = setup({ projects: [validated()], nextVersion: 4 });
    await addButton();
    expect(state.entries).toHaveLength(0);
    await user.click(await addButton());
    expect(await screen.findByText("Ajouté au profil (version 4)")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Ajouter au profil maître" })).toBeNull();
    expect(state.entries).toEqual([
      {
        id: "p1",
        body: {
          name: "Pipeline de ventes",
          description: "Agrégation mensuelle des ventes.",
          achievements: ["Requêtes SQL optimisées", "Test du total"],
        },
      },
    ]);
  });

  it("sends the entry as January retouched it, without blank achievement lines", async () => {
    const { user, state } = setup({ projects: [validated()] });
    const name = await screen.findByLabelText("Nom du projet");
    await user.clear(name);
    await user.type(name, "  Ventes mensuelles  ");
    await user.clear(screen.getByLabelText("Réalisations"));
    await user.type(
      screen.getByLabelText("Réalisations"),
      "Une réalisation{Enter}{Enter}   {Enter}",
    );
    await user.click(await addButton());
    await screen.findByText("Ajouté au profil (version 4)");
    expect(state.entries[0]!.body).toMatchObject({
      name: "Ventes mensuelles",
      achievements: ["Une réalisation"],
    });
  });

  it("sends one request on a double click", async () => {
    const { user, state } = setup({ projects: [validated()] });
    await user.dblClick(await addButton());
    await screen.findByText("Ajouté au profil (version 4)");
    expect(state.entries).toHaveLength(1);
  });

  it("shows a project already in the profile as such", async () => {
    setup({ projects: [validated({ profile_version: 7 })] });
    expect(await screen.findByText("Ajouté au profil (version 7)")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Ajouter au profil maître" })).toBeNull();
    expect(screen.getByLabelText("Nom du projet")).toBeDisabled();
  });

  it("proposes the project name alone when there is no entry draft", async () => {
    const drafts = fourDrafts().filter((draft) => draft.kind !== "profile_entry");
    setup({ projects: [validated({ drafts })] });
    expect(await screen.findByLabelText("Nom du projet")).toHaveValue("Pipeline de ventes");
    expect(screen.getByLabelText("Réalisations")).toHaveValue("");
  });

  it("warns that the entry draft is to check", async () => {
    const drafts = fourDrafts({
      profile_entry: { status: "to_check", flags: ["10000"], entry: undefined },
    });
    setup({ projects: [validated({ drafts })] });
    expect(await screen.findByText(/absent de ton profil et de ton rendu : 10000/)).toBeVisible();
  });

  it.each([
    ["project_not_validated", "Seul un projet validé peut entrer dans ton profil.", false],
    ["entry_already_added", "Ce projet est déjà dans ton profil maître.", false],
    [
      "profile_required",
      "Valide d'abord ton profil maître : le projet s'y ajoute comme une nouvelle version.",
      true,
    ],
    [
      "profile_draft_pending",
      "Un brouillon de profil attend ta validation : valide-le ou écarte-le, puis reviens ajouter ce projet.",
      true,
    ],
    [
      "profile_projects_full",
      "Ton profil maître a déjà 20 projets : retires-en un avant d'en ajouter un.",
      false,
    ],
  ])("writes the 409 %s in clear", async (code, message, withLink) => {
    const { user } = setup({
      projects: [validated()],
      entryReply: () => HttpResponse.json(apiError(code, "Message du serveur."), { status: 409 }),
    });
    await user.click(await addButton());
    const alert = await screen.findByText(message);
    expect(alert).toBeVisible();
    const link = screen.queryByRole("link", { name: "Ouvrir ton profil maître" });
    expect(link !== null).toBe(withLink);
    expect(screen.getByRole("button", { name: "Ajouter au profil maître" })).toBeEnabled();
  });

  it("leads to the master profile from « profile_draft_pending »", async () => {
    const { user, router } = setup({
      projects: [validated()],
      entryReply: () =>
        HttpResponse.json(apiError("profile_draft_pending", "Un brouillon attend."), {
          status: 409,
        }),
    });
    await user.click(await addButton());
    await user.click(await screen.findByRole("link", { name: "Ouvrir ton profil maître" }));
    expect(router.state.location.pathname).toBe("/carriere/profil");
  });
});

describe("ProjectPage : un brouillon seul", () => {
  it("renders a project whose drafts were not generated without a draft card", async () => {
    setup({ projects: [validated({ drafts: [draftOut("cv_line")] })] });
    expect(await screen.findByLabelText("Ligne de CV")).toBeVisible();
    expect(screen.queryByLabelText("Post LinkedIn")).toBeNull();
  });
});
