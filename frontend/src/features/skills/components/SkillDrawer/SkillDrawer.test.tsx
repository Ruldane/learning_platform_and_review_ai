import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { SkillDetailView } from "../viewTypes";
import { SkillDrawer } from "./SkillDrawer";

const detail: SkillDetailView = {
  id: "s2",
  name: "CSS",
  domain: "web",
  synonyms: ["Feuilles de style"],
  level: "en_cours",
  evidence: [
    {
      kind: "lesson",
      label: "Leçon : Sélecteurs",
      at: "2026-11-10T09:00:00Z",
      url: "/apprendre/lecons/l1",
    },
    { kind: "capture", label: "Note rapide", at: "2026-11-11T09:00:00Z", url: null },
  ],
  postings: [],
  nextAction: { kind: "quiz", label: "Passer le quiz « Mise en page »", url: "/etudier/quiz/q1" },
};

function renderDrawer(value: SkillDetailView | null, onClose = vi.fn()) {
  render(
    <MemoryRouter>
      <SkillDrawer detail={value} onClose={onClose} />
    </MemoryRouter>,
  );
  return { onClose };
}

describe("SkillDrawer", () => {
  it("renders nothing without a skill", () => {
    renderDrawer(null);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows evidence links and next action", () => {
    renderDrawer(detail);
    const dialog = screen.getByRole("dialog", { name: "CSS" });
    expect(within(dialog).getByText("Niveau : En cours")).toBeInTheDocument();
    const evidence = within(dialog).getByRole("list", { name: "Preuves" });
    const link = within(evidence).getByRole("link", { name: /Leçon : Sélecteurs/ });
    expect(link).toHaveAttribute("href", "/apprendre/lecons/l1");
    expect(within(evidence).getByText(/Note rapide/)).toBeInTheDocument();
    expect(within(evidence).getAllByRole("link")).toHaveLength(1);
    const next = within(dialog).getByRole("link", { name: "Passer le quiz « Mise en page »" });
    expect(next).toHaveAttribute("href", "/etudier/quiz/q1");
  });

  it("shows empty postings state", () => {
    renderDrawer(detail);
    expect(screen.getByText("Les offres arriveront avec l'analyse d'écart.")).toBeInTheDocument();
  });

  it("lists postings when there are some", () => {
    renderDrawer({
      ...detail,
      postings: [{ id: "p1", title: "Développeuse front", url: "/offres/p1" }],
    });
    expect(screen.getByRole("link", { name: "Développeuse front" })).toHaveAttribute(
      "href",
      "/offres/p1",
    );
    expect(screen.queryByText("Les offres arriveront avec l'analyse d'écart.")).toBeNull();
  });

  it("shows a next action that is not available yet as text", () => {
    renderDrawer({
      ...detail,
      level: "valide",
      nextAction: { kind: "project", label: "Projet preuve (bientôt)", url: null },
    });
    expect(screen.getByText("Projet preuve (bientôt)")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Projet preuve (bientôt)" })).toBeNull();
  });

  it("says nothing is left to do for a proven skill", () => {
    renderDrawer({ ...detail, level: "prouve", nextAction: null });
    expect(
      screen.getByText("Rien à faire de plus : cette compétence est prouvée."),
    ).toBeInTheDocument();
  });

  it("shows an absent skill with no evidence", () => {
    renderDrawer({ ...detail, level: null, evidence: [], synonyms: [] });
    expect(screen.getByText("Niveau : Absent")).toBeInTheDocument();
    expect(screen.getByText("Aucune preuve pour l'instant.")).toBeInTheDocument();
  });

  it("closes with the button and with Escape, and focuses the title", async () => {
    const { onClose } = renderDrawer(detail);
    expect(screen.getByRole("heading", { name: "CSS" })).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: "Fermer" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
