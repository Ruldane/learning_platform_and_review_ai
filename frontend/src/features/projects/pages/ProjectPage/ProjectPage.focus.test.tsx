import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiError } from "@/test/councilHarness";
import { evaluationOut, fourDrafts, projectOut } from "@/test/projectsApi";
import { renderProjects } from "@/test/projectsHarness";
import { server } from "@/test/server";
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
    drafts: fourDrafts(),
    ...over,
  });

const notBody = () => expect(document.activeElement).not.toBe(document.body);

describe("ProjectPage : le focus ne tombe jamais sur body", () => {
  it("keeps the focus on « Enregistrer » after a draft is saved", async () => {
    const { user } = setup({ projects: [validated()] });
    const area = (await screen.findAllByLabelText("Ligne de CV"))[0]!;
    await user.type(area, " plus");
    const save = area.closest("article")!.querySelector("button")!;
    save.focus();
    await user.keyboard("{Enter}");
    await screen.findByText("Retouché par toi");
    expect(save).toHaveFocus();
    expect(save).not.toBeDisabled();
  });

  it("moves the focus to the review title after « Rendre le projet »", async () => {
    const { user } = setup({ projects: [projectOut("p1")] });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    await user.click(await screen.findByRole("button", { name: "Rendre le projet" }));
    const title = await screen.findByRole("heading", { name: "Évaluation en cours" });
    expect(title).toHaveFocus();
  });

  it("moves the focus to the brief title after « Réessayer l'énoncé »", async () => {
    const failed = projectOut("p1", { status: "brief_failed", brief: null });
    const { user } = setup({ projects: [failed] });
    await user.click(await screen.findByRole("button", { name: "Réessayer l'énoncé" }));
    const title = await screen.findByRole("heading", { name: "Énoncé en cours d'écriture" });
    expect(title).toHaveFocus();
  });

  it("moves the focus to the added status once the entry is in the profile", async () => {
    const { user } = setup({ projects: [validated()] });
    await user.click(await screen.findByRole("button", { name: "Ajouter au profil maître" }));
    const status = await screen.findByText("Ajouté au profil (version 4)");
    expect(status).toHaveFocus();
  });

  it("keeps the focus on the add button when the addition fails", async () => {
    const { user } = setup({
      projects: [validated()],
      entryReply: () => HttpResponse.json(apiError("entry_failed", "Panne."), { status: 500 }),
    });
    const add = await screen.findByRole("button", { name: "Ajouter au profil maître" });
    await user.click(add);
    await screen.findByRole("alert");
    expect(add).toHaveFocus();
    notBody();
  });

  it("does not add the entry to the master profile when Enter is pressed in the name field", async () => {
    const { user, state } = setup({ projects: [validated()] });
    const name = await screen.findByLabelText("Nom du projet");
    await user.click(name);
    await user.keyboard("{Enter}");
    expect(state.entries).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Ajouter au profil maître" })).toBeVisible();
  });
});

describe("ProjectPage : le titre de la page", () => {
  it("has a level-one title while the project loads", async () => {
    setup({ projects: [projectOut("p1")] });
    expect(screen.getByRole("heading", { level: 1, name: "Projet" })).toBeVisible();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Pipeline de ventes" }),
    ).toBeVisible();
  });

  it("has a level-one title when the read fails", async () => {
    setup({ projects: [] });
    server.use(
      http.get("*/api/v1/projects/:id", () =>
        HttpResponse.json(apiError("internal_error", "Panne."), { status: 500 }),
      ),
    );
    expect(
      await screen.findByRole("button", { name: /Réessayer/ }, { timeout: 4000 }),
    ).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Projet" })).toBeVisible();
  });
});
