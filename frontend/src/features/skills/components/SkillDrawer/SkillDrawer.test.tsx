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
  level: "in_progress",
  evidence: [
    {
      kind: "lesson",
      label: "Leçon : Sélecteurs",
      at: "2026-11-10T09:00:00Z",
      url: "/learn/lessons/l1",
    },
    { kind: "capture", label: "Note rapide", at: "2026-11-11T09:00:00Z", url: null },
  ],
  postings: [],
  nextAction: { kind: "quiz", label: "Passer le quiz « Mise en page »", url: "/study/quiz/q1" },
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
    expect(within(dialog).getByText("Level: In progress")).toBeInTheDocument();
    const evidence = within(dialog).getByRole("list", { name: "Evidence" });
    const link = within(evidence).getByRole("link", { name: /Leçon : Sélecteurs/ });
    expect(link).toHaveAttribute("href", "/learn/lessons/l1");
    expect(within(evidence).getByText(/Note rapide/)).toBeInTheDocument();
    expect(within(evidence).getAllByRole("link")).toHaveLength(1);
    const next = within(dialog).getByRole("link", { name: "Passer le quiz « Mise en page »" });
    expect(next).toHaveAttribute("href", "/study/quiz/q1");
  });

  it("shows empty postings state", () => {
    renderDrawer(detail);
    expect(screen.getByText("No added posting requires this skill.")).toBeInTheDocument();
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
    expect(screen.queryByText("No added posting requires this skill.")).toBeNull();
  });

  it("shows a next action that is not available yet as text", () => {
    renderDrawer({
      ...detail,
      level: "validated",
      nextAction: { kind: "project", label: "Projet preuve (bientôt)", url: null },
    });
    expect(screen.getByText("Projet preuve (bientôt)")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Projet preuve (bientôt)" })).toBeNull();
  });

  it("says nothing is left to do for a proven skill", () => {
    renderDrawer({ ...detail, level: "proven", nextAction: null });
    expect(
      screen.getByText("Nothing more to do: this skill is proven."),
    ).toBeInTheDocument();
  });

  it("shows an absent skill with no evidence", () => {
    renderDrawer({ ...detail, level: null, evidence: [], synonyms: [] });
    expect(screen.getByText("Level: Missing")).toBeInTheDocument();
    expect(screen.getByText("No evidence yet.")).toBeInTheDocument();
  });

  it("closes with the button and with Escape, and focuses the title", async () => {
    const { onClose } = renderDrawer(detail);
    expect(screen.getByRole("heading", { name: "CSS" })).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("lists a phase 4 evidence without a date", () => {
    renderDrawer({
      ...detail,
      evidence: [{ kind: "program", label: "Programme web", at: null, url: null }],
    });
    expect(screen.getByText("Programme web")).toBeInTheDocument();
    expect(screen.queryByText(/Invalid Date/)).toBeNull();
  });
});
