import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { makeDebrief, makeExchange, makeInterview } from "../fixtures";
import type { InterviewView } from "../viewTypes";
import { DebriefView } from "./DebriefView";

function show(interview: InterviewView = makeInterview()) {
  render(
    <MemoryRouter>
      <DebriefView interview={interview} reviewsHref="/etudier/revisions" />
    </MemoryRouter>,
  );
}

describe("DebriefView", () => {
  it("shows the four scores out of five as text and as a bar, never colour alone", () => {
    show();
    const scores = within(screen.getByRole("list", { name: "Tes notes" }));
    const rows = scores.getAllByRole("listitem");
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent("Clarté");
    expect(rows[0]).toHaveTextContent("4 sur 5");
    expect(rows[2]).toHaveTextContent("Profondeur technique");
    expect(rows[2]).toHaveTextContent("2 sur 5");
    expect(rows[3]).toHaveTextContent("Adéquation au poste");
    expect(rows[3]).toHaveTextContent("5 sur 5");
    const bar = within(rows[0]!).getByTestId("score-bar");
    expect(bar).toHaveAttribute("aria-hidden", "true");
    expect(bar.firstElementChild).toHaveStyle({ width: "80%" });
  });

  it("says « non noté » for a score the model did not give, and leaves the average out of it", () => {
    const base = makeInterview();
    show({
      ...base,
      debrief: {
        ...base.debrief!,
        scores: [
          { key: "clarte", value: 4 },
          { key: "structure", value: null },
          { key: "profondeur_technique", value: 2 },
          { key: "adequation", value: 5 },
        ],
      },
    });
    const rows = within(screen.getByRole("list", { name: "Tes notes" })).getAllByRole("listitem");
    expect(rows[1]).toHaveTextContent("Structure");
    expect(rows[1]).toHaveTextContent("non noté");
    expect(rows[1]).not.toHaveTextContent("0 sur 5");
    expect(within(rows[1]!).getByTestId("score-bar").firstElementChild).toHaveStyle({
      width: "0%",
    });
  });

  it("lists the three strengths and the three things to fix", () => {
    show();
    const strengths = screen.getByRole("heading", { name: "Tes points forts" });
    expect(strengths.nextElementSibling?.querySelectorAll("li")).toHaveLength(3);
    expect(screen.getByText("Résultats chiffrés")).toBeVisible();
    const fixes = screen.getByRole("heading", { name: "Tes points à corriger" });
    expect(fixes.nextElementSibling?.querySelectorAll("li")).toHaveLength(3);
    expect(screen.getByText("Une conclusion")).toBeVisible();
  });

  it("shows the improved answer for the weakest question, clean when nothing is flagged", () => {
    show();
    expect(screen.getByRole("heading", { name: "Réponse améliorée" })).toBeVisible();
    expect(screen.getByText("Pour la question 2 : « Question 2 du recruteur ? »")).toBeVisible();
    expect(screen.getByText("Voici une réponse mieux construite.")).toBeVisible();
    expect(screen.queryByText("À vérifier")).toBeNull();
  });

  it("marks the improved answer « à vérifier » with the terms the profile does not say", () => {
    show(makeInterview({ flags: ["Kubernetes", "Terraform"] }));
    expect(screen.getByText("À vérifier")).toBeVisible();
    expect(screen.getByRole("note")).toHaveTextContent(
      "Ces termes ne sont pas dans ton profil : Kubernetes, Terraform.",
    );
  });

  it("says how many revision cards were created and links to the revisions", () => {
    show(makeInterview({ cardsCreated: 3 }));
    expect(screen.getByText("3 fiches de révision ont été créées, à revoir demain.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Ouvrir mes révisions" })).toHaveAttribute(
      "href",
      "/etudier/revisions",
    );
  });

  it("says so when no card was created, with no link", () => {
    show(makeInterview({ cardsCreated: 0 }));
    expect(screen.getByText("Aucune nouvelle fiche de révision n'a été créée.")).toBeVisible();
    expect(screen.queryByRole("link", { name: "Ouvrir mes révisions" })).toBeNull();
  });

  it("uses the singular for one card", () => {
    show(makeInterview({ cardsCreated: 1 }));
    expect(screen.getByText("1 fiche de révision a été créée, à revoir demain.")).toBeVisible();
  });

  it("says which answers could not be rated, and marks them in the answers", () => {
    show(
      makeInterview({
        debrief: makeDebrief({ unrated: [0, 2] }),
        exchanges: [
          makeExchange(0, { unrated: true }),
          makeExchange(1, { note: 2 }),
          makeExchange(2, { unrated: true }),
        ],
      }),
    );
    expect(
      screen.getByText(
        "Les réponses aux questions 1 et 3 n'ont pas pu être notées : elles ne comptent pas dans les notes.",
      ),
    ).toBeVisible();
    expect(screen.getAllByText("Non notée")).toHaveLength(2);
  });

  it("uses the singular for one unrated answer", () => {
    show(makeInterview({ debrief: makeDebrief({ unrated: [1] }) }));
    expect(
      screen.getByText(
        "La réponse à la question 2 n'a pas pu être notée : elle ne compte pas dans les notes.",
      ),
    ).toBeVisible();
  });

  it("shows each answer with its note, and what a good answer would have said for a missed one", () => {
    show();
    const answers = within(screen.getByRole("region", { name: "Tes réponses" }));
    const second = within(answers.getByRole("article", { name: "Question 2" }));
    expect(second.getByText("Question 2 du recruteur ?")).toBeVisible();
    expect(second.getByText("Ma réponse 2.")).toBeVisible();
    expect(second.getByText("Note : 2 sur 5")).toBeVisible();
    expect(second.getByText("À revoir")).toBeVisible();
    expect(second.getByText("Citer le contexte")).toBeVisible();
    const first = within(answers.getByRole("article", { name: "Question 1" }));
    expect(first.getByText("Note : 4 sur 5")).toBeVisible();
    expect(first.queryByText("À revoir")).toBeNull();
  });

  it("shows the follow-up and its answer", () => {
    show(
      makeInterview({
        exchanges: [
          makeExchange(0, { followUp: "Peux-tu préciser ?", followUpAnswer: "Bien sûr, voilà." }),
        ],
      }),
    );
    expect(screen.getByText("Peux-tu préciser ?")).toBeVisible();
    expect(screen.getByText("Bien sûr, voilà.")).toBeVisible();
  });
});
