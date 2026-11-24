import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { councilEvents } from "@/test/councilEvents";
import { apiError } from "@/test/councilHarness";
import {
  briefOut,
  criterionOut,
  evaluationOut,
  projectOut,
  submissionOut,
} from "@/test/projectsApi";
import { openStream, renderProjects } from "@/test/projectsHarness";
import * as projectsApiModule from "../../api";
import { PortfolioPage } from "../PortfolioPage";
import { ProjectPage } from "./ProjectPage";

const setup = (
  api: Parameters<typeof renderProjects>[1] = {},
  path = "/skills/portfolio/p1",
) =>
  renderProjects(
    (createSocket) => ({
      portfolio: <PortfolioPage />,
      project: <ProjectPage createSocket={createSocket} />,
    }),
    api,
    path,
  );

// Le corps multipart n'est pas relisible sous jsdom : on observe ce que la page passe à l'appel.
const submitSpy = vi.spyOn(projectsApiModule, "submitProject");
beforeEach(() => {
  submitSpy.mockClear();
});

const TODO = projectOut("p1");
const submitButton = () => screen.findByRole("button", { name: "Submit the project" });
const png = (name: string) => new File([new Uint8Array(20)], name, { type: "image/png" });

describe("ProjectPage : l'énoncé", () => {
  it("shows the brief: context, objective, constraints, criteria, hours", async () => {
    setup({ projects: [TODO] });
    expect(
      await screen.findByRole("heading", { level: 1, name: "Pipeline de ventes" }),
    ).toBeVisible();
    expect(screen.getByText("Status: To do")).toBeVisible();
    expect(screen.getByText("Un export CSV de ventes sans identité réelle.")).toBeVisible();
    expect(screen.getByText("Agréger les ventes de « Société Fictive » par mois.")).toBeVisible();
    expect(screen.getByText("SQL uniquement")).toBeVisible();
    expect(screen.getByText("Un test vérifie le total")).toBeVisible();
    expect(screen.getByText("Estimated time: 6 h")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to Portfolio" })).toHaveAttribute(
      "href",
      "/skills/portfolio",
    );
  });

  it("says a project is missing", async () => {
    setup({ projects: [] }, "/skills/portfolio/nope");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Project not found" }),
    ).toBeVisible();
  });

  it("follows the brief being written, then shows it when the session ends", async () => {
    const pending = projectOut("p1", {
      status: "brief_pending",
      brief: null,
      session_id: "sess-brief",
    });
    const { settle, sockets } = setup({ projects: [pending] });
    expect(
      await screen.findByRole("heading", { name: "Brief being written" }),
    ).toBeVisible();
    const stream = await openStream(sockets, "sess-brief");
    const events = councilEvents("sess-brief");
    stream.push(events.message("m1", "J'écris l'énoncé du projet.", "practitioner"));
    expect(await screen.findByText("J'écris l'énoncé du projet.")).toBeVisible();
    settle("p1", { status: "todo", brief: briefOut() });
    stream.push(events.completed());
    expect(
      await screen.findByText("Agréger les ventes de « Société Fictive » par mois."),
    ).toBeVisible();
    expect(await submitButton()).toHaveAttribute("aria-disabled", "false");
  });

  it("offers « Réessayer l'énoncé » when the brief failed, and follows the new session", async () => {
    const failed = projectOut("p1", { status: "brief_failed", brief: null });
    const { user, state, sockets } = setup({ projects: [failed] });
    await user.click(await screen.findByRole("button", { name: "Retry the brief" }));
    expect(state.briefs).toEqual(["p1"]);
    expect(
      await screen.findByRole("heading", { name: "Brief being written" }),
    ).toBeVisible();
    await openStream(sockets, "sess-brief-p1");
    expect(screen.queryByRole("button", { name: "Retry the brief" })).toBeNull();
  });

  it("sends one brief retry on a double click", async () => {
    const failed = projectOut("p1", { status: "brief_failed", brief: null });
    const { user, state } = setup({ projects: [failed] });
    await user.dblClick(await screen.findByRole("button", { name: "Retry the brief" }));
    await screen.findByRole("heading", { name: "Brief being written" });
    expect(state.briefs).toEqual(["p1"]);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("starts from a clean page when another project is opened", async () => {
    const other = projectOut("p2", { title: "Autre projet" });
    const { user, router } = setup({ projects: [TODO, other] });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    await router.navigate("/skills/portfolio/p2");
    expect(await screen.findByRole("heading", { level: 1, name: "Autre projet" })).toBeVisible();
    expect(screen.getByLabelText("Description")).toHaveValue("");
  });

  it("reads « brief_not_failed » in clear when the brief was already relaunched", async () => {
    const failed = projectOut("p1", { status: "brief_failed", brief: null });
    const { user } = setup({
      projects: [failed],
      briefReply: () =>
        HttpResponse.json(apiError("brief_not_failed", "L'énoncé n'est pas en échec."), {
          status: 409,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Retry the brief" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This project’s brief hasn’t failed: it may already have been retried.",
    );
  });
});

describe("ProjectPage : rendre le projet et suivre l'évaluation", () => {
  it("sends the submission as multipart, follows the review, then shows the evaluation", async () => {
    const { user, state, settle, sockets } = setup({ projects: [TODO] });
    await user.type(
      await screen.findByLabelText("Repository link"),
      "https://example.org/camille/ventes",
    );
    await user.type(screen.getByLabelText("Description"), "Une requête SQL.");
    await user.upload(screen.getByLabelText("Screenshots"), [png("a.png"), png("b.png")]);
    await user.click(await submitButton());

    await waitFor(() => expect(state.submits).toHaveLength(1));
    expect(state.submits[0]!.contentType).toMatch(/^multipart\/form-data; boundary=/);
    const [id, sent] = submitSpy.mock.calls[0]!;
    expect(id).toBe("p1");
    expect(sent).toMatchObject({
      repoUrl: "https://example.org/camille/ventes",
      description: "Une requête SQL.",
    });
    expect(sent.screenshots.map((file) => file.name)).toEqual(["a.png", "b.png"]);

    expect(await screen.findByRole("heading", { name: "Review in progress" })).toBeVisible();
    expect(screen.getByText("Status: Under review")).toBeVisible();
    expect(screen.queryByRole("form", { name: "Submit your project" })).toBeNull();
    const stream = await openStream(sockets, "sess-p1-1");
    const events = councilEvents("sess-p1-1");
    stream.push(events.message("m1", "Je lis ton dépôt.", "practitioner"));
    expect(await screen.findByText("Je lis ton dépôt.")).toBeVisible();

    settle("p1", {
      status: "to_redo",
      evaluation: evaluationOut({
        results: [
          criterionOut(3, false, "Le README est vide."),
          criterionOut(1, true, "La requête groupe par mois."),
        ],
      }),
    });
    stream.push(events.completed());
    expect(await screen.findByText("Project to redo")).toBeVisible();
    const checklist = screen.getByRole("list", { name: "Result for each criterion" });
    const items = within(checklist).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Ventes agrégées par mois");
    expect(items[0]).toHaveTextContent("La requête groupe par mois.");
    expect(items[1]).toHaveTextContent("Not reviewed yet");
    expect(items[2]).toHaveTextContent("Le README est vide.");
  });

  it("sends only one submission on a double click", async () => {
    const { user, state } = setup({ projects: [TODO] });
    await user.type(await screen.findByLabelText("Description"), "Une requête SQL.");
    await user.dblClick(await submitButton());
    await screen.findByRole("heading", { name: "Review in progress" });
    expect(state.submits).toHaveLength(1);
    expect(submitSpy).toHaveBeenCalledTimes(1);
    // Un second envoi aurait reçu un 409 `review_in_progress` et la page l'aurait dit.
    expect(screen.queryByText("A review was already in progress: following it.")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the screenshots of every submission as thumbnails, the latest first", async () => {
    const project = projectOut("p1", {
      status: "to_redo",
      evaluation: evaluationOut(),
      submissions: [
        submissionOut({
          at: "2026-11-16T12:00:00Z",
          screenshots: 2,
          description: "Deuxième rendu.",
        }),
        submissionOut({
          at: "2026-11-15T12:00:00Z",
          screenshots: 1,
          description: "Premier rendu.",
        }),
      ],
    });
    setup({ projects: [project] });
    const history = await screen.findByRole("region", { name: "Your submissions" });
    const card = (day: string) =>
      within(history)
        .getByRole("heading", { name: new RegExp(`Submission of ${day}`) })
        .closest("li")!;
    const latest = card("16 November 2026");
    const older = card("15 November 2026");
    expect(latest).toHaveTextContent("Deuxième rendu.");
    const latestShots = within(latest).getAllByRole("img");
    expect(latestShots.map((img) => img.getAttribute("src"))).toEqual([
      expect.stringMatching(/\/projects\/p1\/screenshots\/1\?submission=1$/),
      expect.stringMatching(/\/projects\/p1\/screenshots\/2\?submission=1$/),
    ]);
    expect(within(older).getByRole("img")).toHaveAttribute(
      "src",
      expect.stringMatching(/\/projects\/p1\/screenshots\/1\?submission=2$/),
    );
    expect(within(latest).getByRole("link", { name: /example\.org/ })).toHaveAttribute(
      "rel",
      "noopener noreferrer",
    );
  });

  it("shows the previous evaluation and the form again for a project to redo", async () => {
    const project = projectOut("p1", { status: "to_redo", evaluation: evaluationOut() });
    setup({ projects: [project] });
    expect(await screen.findByText("Project to redo")).toBeVisible();
    expect(
      screen.getByText("To rework: fix what’s missing, then submit your project again."),
    ).toBeVisible();
    expect(await submitButton()).toHaveAttribute("aria-disabled", "false");
  });
});
