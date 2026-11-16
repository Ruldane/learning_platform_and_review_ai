import { screen, waitFor } from "@testing-library/react";
import { HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { apiError } from "@/test/councilHarness";
import { projectOut, submissionOut } from "@/test/projectsApi";
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

const TODO = projectOut("p1");
const submitButton = () => screen.findByRole("button", { name: "Rendre le projet" });
const png = (name: string) => new File([new Uint8Array(20)], name, { type: "image/png" });

describe("ProjectPage : refus du serveur", () => {
  const refuse = (status: number, code: string, message: string, details: unknown = null) => ({
    submitReply: () => HttpResponse.json(apiError(code, message, details), { status }),
  });

  it("attaches a 422 to the field it names, without echoing any value", async () => {
    const { user } = setup({
      projects: [TODO],
      ...refuse(422, "validation_error", "Requête invalide.", { fields: ["repo_url"] }),
    });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    await user.click(await submitButton());
    const repo = await screen.findByLabelText("Lien du dépôt");
    await waitFor(() => expect(repo).toBeInvalid());
    expect(repo).toHaveAccessibleDescription(/adresse http ou https/);
    expect(screen.getByLabelText("Description")).toBeValid();
    await user.type(repo, "https://example.org/camille");
    expect(repo).toBeValid();
  });

  it("attaches « screenshots.N » to the screenshots", async () => {
    const { user } = setup({
      projects: [TODO],
      ...refuse(422, "validation_error", "Requête invalide.", { fields: ["screenshots.1"] }),
    });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    await user.upload(screen.getByLabelText("Captures d'écran"), png("a.png"));
    await user.click(await submitButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Une capture n'est pas acceptée");
    expect(screen.getByLabelText("Captures d'écran")).toBeInvalid();
    expect(screen.getByLabelText("Description")).toBeValid();
  });

  it("asks for a link or a description when the server names both", async () => {
    const { user } = setup({
      projects: [TODO],
      ...refuse(422, "validation_error", "Requête invalide.", {
        fields: ["repo_url", "description"],
      }),
    });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    await user.click(await submitButton());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ajoute un lien de dépôt ou une description.",
    );
  });

  it.each([
    [
      409,
      "project_not_ready",
      "L'énoncé de ce projet n'est pas encore écrit : attends-le avant de rendre ton travail.",
    ],
    [413, "file_too_large", "Une capture est trop volumineuse : 5 Mo au plus chacune."],
    [503, "review_unavailable", "L'évaluation n'a pas pu démarrer : réessaie dans un instant."],
  ])("writes the refusal %i %s in clear", async (status, code, message) => {
    const { user } = setup({ projects: [TODO], ...refuse(status, code, message) });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    await user.click(await submitButton());
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(await submitButton()).toHaveAttribute("aria-disabled", "false");
  });

  it("follows the review already in progress (409 review_in_progress) instead of failing", async () => {
    const { user, settle, sockets } = setup({
      projects: [TODO],
      ...refuse(409, "review_in_progress", "Ton rendu est en cours d'évaluation.", {
        session_id: "sess-open",
      }),
    });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    settle("p1", { status: "reviewing", session_id: "sess-open", submissions: [submissionOut()] });
    await user.click(await submitButton());
    expect(await screen.findByRole("heading", { name: "Évaluation en cours" })).toBeVisible();
    expect(screen.getByText("Une évaluation était déjà en cours : on la suit.")).toBeVisible();
    await openStream(sockets, "sess-open");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("re-reads a project validated elsewhere (409 project_validated) and says so", async () => {
    const { user, settle } = setup({
      projects: [TODO],
      ...refuse(409, "project_validated", "Ce projet est déjà validé."),
    });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    settle("p1", { status: "validated", validated_at: "2026-11-16T12:00:00Z" });
    await user.click(await submitButton());
    expect(await screen.findByRole("heading", { name: "Projet validé" })).toBeVisible();
    expect(screen.queryByRole("form", { name: "Rendre ton projet" })).toBeNull();
  });
});
