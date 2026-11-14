import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import {
  analyzingPosting,
  gapOut,
  gapRow,
  postingOut,
  postingsApi,
  refusal,
} from "@/test/postingsApi";
import { renderPosting } from "@/test/postingsHarness";
import { PostingPage } from "./PostingPage";

function setup(api: Parameters<typeof postingsApi>[0] = {}) {
  return renderPosting((createSocket) => <PostingPage createSocket={createSocket} />, api);
}

const analyzing = analyzingPosting;

describe("PostingPage", () => {
  beforeEach(() => useSessionStore.getState().reset("a1"));
  afterEach(() => useSessionStore.getState().reset("a1"));

  it("shows the analysis, the score and the gap table of a ready posting", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { level: 1, name: "Ingénieure données" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Société Fictive")).toBeInTheDocument();
    expect(await screen.findByText("62/100")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Écart avec l'offre" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Revoir mon CV pour cette offre" })).toHaveAttribute(
      "href",
      "/carriere/cv/revue/nouvelle/p1",
    );
  });

  it("offers only the rows that are really missing and sends the ticked skills", async () => {
    const { user, state } = setup();
    const python = await screen.findByRole("checkbox", { name: "Ajouter Python au planning" });
    expect(screen.queryByRole("checkbox", { name: "Ajouter SQL au planning" })).toBeNull();
    expect(screen.queryByRole("checkbox", { name: "Ajouter Go au planning" })).toBeNull();
    expect(screen.getByText("Déjà acquise")).toBeInTheDocument();
    await user.click(python);
    await user.click(screen.getByRole("checkbox", { name: "Ajouter Docker au planning" }));
    await user.click(screen.getByRole("button", { name: "Ajouter au planning (2)" }));
    expect(await screen.findByText(/Replanification lancée/)).toBeInTheDocument();
    expect(state.plans).toEqual([{ skills: ["Python", "Docker"] }]);
    await user.click(screen.getByRole("link", { name: "Ouvrir la replanification" }));
    expect(await screen.findByText("Replanification")).toBeInTheDocument();
  });

  it("says in French that there is no program yet and offers to create a goal", async () => {
    const { user } = setup({
      plan: () => refusal(409, "no_program", "Message du serveur."),
    });
    await user.click(await screen.findByRole("checkbox", { name: "Ajouter Python au planning" }));
    await user.click(screen.getByRole("button", { name: "Ajouter au planning (1)" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("pas encore de programme validé");
    await user.click(screen.getByRole("link", { name: "Créer un objectif" }));
    expect(await screen.findByText("Objectifs")).toBeInTheDocument();
  });

  it("links to the replan already open (409 replan_open)", async () => {
    const { user } = setup({
      plan: () => refusal(409, "replan_open", "Message du serveur.", { session_id: "r1" }),
    });
    await user.click(await screen.findByRole("checkbox", { name: "Ajouter Python au planning" }));
    await user.click(screen.getByRole("button", { name: "Ajouter au planning (1)" }));
    expect(await screen.findByText("Une replanification est déjà ouverte.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ouvrir la replanification" })).toHaveAttribute(
      "href",
      "/apprendre/programme/pg1/replanification",
    );
  });

  it("rereads the table when a skill is no longer to add (422)", async () => {
    const { user, state } = setup({
      plan: () =>
        refusal(422, "gap_skill_unknown", "Message du serveur.", { fields: ["skills.0"] }),
      gaps: [
        gapOut(),
        gapOut({ rows: [gapRow("Python", { action: "in_program", week: 2 }), gapRow("Docker")] }),
      ],
    });
    await user.click(await screen.findByRole("checkbox", { name: "Ajouter Python au planning" }));
    await user.click(screen.getByRole("button", { name: "Ajouter au planning (1)" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("n'est plus à ajouter");
    await waitFor(() => expect(state.reads.gap).toBe(2));
    expect(await screen.findByText("Dans ton programme, semaine 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ajouter au planning" })).toBeDisabled();
  });

  it("shows probable duplicates and marks two postings as distinct", async () => {
    const duplicate = {
      level: "probable",
      posting_id: "p7",
      title: "Ingénieur données",
      company: "Société Fictive",
      created_at: "2026-11-01T10:00:00Z",
    };
    const { user, state } = setup({
      postings: [postingOut({ duplicates: [duplicate] }), postingOut()],
    });
    expect(await screen.findByText("Offre très proche d'une offre déjà ajoutée.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Ce sont deux offres distinctes" }));
    await waitFor(() => expect(state.distincts).toEqual([{ other_id: "p7" }]));
    await waitFor(() =>
      expect(screen.queryByText("Offre très proche d'une offre déjà ajoutée.")).toBeNull(),
    );
  });

  it("confirms the deletion in the page, never with window.confirm", async () => {
    const confirm = vi.spyOn(window, "confirm");
    const { user, state } = setup();
    await user.click(await screen.findByRole("button", { name: "Supprimer l'offre" }));
    const ask = screen.getByRole("group", { name: "Supprimer cette offre ?" });
    expect(within(ask).getByRole("button", { name: "Annuler" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("group", { name: "Supprimer cette offre ?" })).toBeNull();
    expect(state.removed).toBe(0);
    await user.click(screen.getByRole("button", { name: "Supprimer l'offre" }));
    await user.click(screen.getByRole("button", { name: "Oui, supprimer" }));
    expect(await screen.findByText("Liste des offres")).toBeInTheDocument();
    expect(state.removed).toBe(1);
    expect(confirm).not.toHaveBeenCalled();
  });

  it("shows a rejected posting without relaunch", async () => {
    setup({
      postings: [
        postingOut({
          status: "rejected",
          title: null,
          analysis: null,
          failure_reason: "Ce texte décrit une entreprise, pas un poste.",
        }),
      ],
    });
    expect(
      await screen.findByRole("heading", { name: "Refusée : ce n'est pas une offre" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Ce texte décrit une entreprise, pas un poste.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Relancer l'analyse" })).toBeNull();
    expect(screen.getByRole("button", { name: "Supprimer l'offre" })).toBeInTheDocument();
  });

  it("relaunches an interrupted analysis", async () => {
    const { user, state } = setup({
      postings: [
        postingOut({
          status: "failed",
          analysis: null,
          failure_reason: "L'analyse s'est arrêtée.",
        }),
        analyzing(),
      ],
    });
    await user.click(await screen.findByRole("button", { name: "Relancer l'analyse" }));
    expect(await screen.findByText("Analyse en cours…")).toBeInTheDocument();
    expect(state.relaunched).toBe(1);
  });

  it("follows the relaunch of an analysis already running (409 gap_in_progress)", async () => {
    const { user } = setup({
      postings: [postingOut({ status: "failed", analysis: null }), analyzing()],
      relaunch: () => refusal(409, "gap_in_progress", "Message du serveur."),
    });
    await user.click(await screen.findByRole("button", { name: "Relancer l'analyse" }));
    expect(await screen.findByText("Analyse en cours…")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("waits for a gap being computed, then relaunches a failed one", async () => {
    const { user } = setup({ gaps: [gapOut({ status: "failed", score: null, rows: [] })] });
    expect(await screen.findByText("L'écart n'a pas pu être calculé.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Relancer l'analyse" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Relancer l'analyse" })).toBeEnabled(),
    );
  });

  it("says when the posting does not exist", async () => {
    const { user } = setup({
      posting: () => refusal(404, "posting_not_found", "Introuvable."),
    });
    expect(await screen.findByText("Offre introuvable")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retour aux offres" }));
    expect(await screen.findByText("Liste des offres")).toBeInTheDocument();
  });

  it("shows a retryable error", async () => {
    let failing = true;
    const { user } = setup({
      posting: () =>
        failing
          ? refusal(500, "internal_error", "Panne du serveur.")
          : HttpResponse.json(postingOut()),
    });
    expect(await screen.findByText("Panne du serveur.", {}, { timeout: 4000 })).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Ingénieure données" }),
    ).toBeInTheDocument();
  });
});
