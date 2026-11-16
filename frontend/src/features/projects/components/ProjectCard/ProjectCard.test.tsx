import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { PROJECT_STATUSES, type ProjectCardView } from "../viewTypes";
import { ProjectCard } from "./ProjectCard";

const PROJECT: ProjectCardView = {
  id: "p1",
  title: "Pipeline de ventes",
  status: "todo",
  hours: 6,
  skills: ["SQL", "dbt"],
  href: "/projets/p1",
};

const view = (project: ProjectCardView) =>
  render(
    <MemoryRouter>
      <ProjectCard project={project} />
    </MemoryRouter>,
  );

describe("ProjectCard", () => {
  it("shows the title as a link, the status in words, the hours and the skills", () => {
    view(PROJECT);
    expect(screen.getByRole("link", { name: "Pipeline de ventes" })).toHaveAttribute(
      "href",
      "/projets/p1",
    );
    expect(screen.getByText("Statut : À faire")).toBeInTheDocument();
    expect(screen.getByText("6 h estimées")).toBeInTheDocument();
    expect(screen.getByText("Compétences : SQL, dbt")).toBeInTheDocument();
  });

  it.each([
    ["brief_pending", "Énoncé en préparation"],
    ["brief_failed", "Énoncé impossible à écrire"],
    ["todo", "À faire"],
    ["reviewing", "En cours d'évaluation"],
    ["to_redo", "À refaire"],
    ["validated", "Validé"],
  ] as const)("writes the status %s as « %s »", (status, label) => {
    view({ ...PROJECT, status });
    expect(screen.getByText(`Statut : ${label}`)).toBeInTheDocument();
  });

  it("knows every status of the contract", () => {
    expect(PROJECT_STATUSES).toHaveLength(6);
  });

  it("is plain text without an address, and says nothing of hours that are not known yet", () => {
    view({ id: "p2", title: PROJECT.title, status: "todo", hours: null, skills: [] });
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByRole("heading", { level: 3, name: "Pipeline de ventes" })).toBeVisible();
    expect(screen.queryByText(/estimées/)).toBeNull();
    expect(screen.queryByText(/Compétences/)).toBeNull();
  });
});
