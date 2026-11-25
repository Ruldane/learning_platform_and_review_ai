import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { makeDebrief, makeExchange, makeInterview } from "../fixtures";
import type { InterviewView } from "../viewTypes";
import { DebriefView } from "./DebriefView";

function show(interview: InterviewView = makeInterview()) {
  render(
    <MemoryRouter>
      <DebriefView interview={interview} reviewsHref="/study/reviews" />
    </MemoryRouter>,
  );
}

describe("DebriefView", () => {
  it("shows the four scores out of five as text and as a bar, never colour alone", () => {
    show();
    const scores = within(screen.getByRole("list", { name: "Your scores" }));
    const rows = scores.getAllByRole("listitem");
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent("Clarity");
    expect(rows[0]).toHaveTextContent("4 out of 5");
    expect(rows[2]).toHaveTextContent("Technical depth");
    expect(rows[2]).toHaveTextContent("2 out of 5");
    expect(rows[3]).toHaveTextContent("Fit for the role");
    expect(rows[3]).toHaveTextContent("5 out of 5");
    const bar = within(rows[0]!).getByTestId("score-bar");
    expect(bar).toHaveAttribute("aria-hidden", "true");
    expect(bar.firstElementChild).toHaveStyle({ width: "80%" });
  });

  it("omits the average and labels a missing score “not scored”", () => {
    const base = makeInterview();
    show({
      ...base,
      debrief: {
        ...base.debrief!,
        scores: [
          { key: "clarity", value: 4 },
          { key: "structure", value: null },
          { key: "technical_depth", value: 2 },
          { key: "role_fit", value: 5 },
        ],
      },
    });
    const rows = within(screen.getByRole("list", { name: "Your scores" })).getAllByRole("listitem");
    expect(rows[1]).toHaveTextContent("Structure");
    expect(rows[1]).toHaveTextContent("not scored");
    expect(rows[1]).not.toHaveTextContent("0 out of 5");
    expect(within(rows[1]!).getByTestId("score-bar").firstElementChild).toHaveStyle({
      width: "0%",
    });
  });

  it("lists the three strengths and the three things to fix", () => {
    show();
    const strengths = screen.getByRole("heading", { name: "Your strengths" });
    expect(strengths.nextElementSibling?.querySelectorAll("li")).toHaveLength(3);
    expect(screen.getByText("Résultats chiffrés")).toBeVisible();
    const fixes = screen.getByRole("heading", { name: "What to fix" });
    expect(fixes.nextElementSibling?.querySelectorAll("li")).toHaveLength(3);
    expect(screen.getByText("Une conclusion")).toBeVisible();
  });

  it("shows the improved answer for the weakest question, clean when nothing is flagged", () => {
    show();
    expect(screen.getByRole("heading", { name: "Improved answer" })).toBeVisible();
    expect(screen.getByText("For question 2: “Question 2 du recruteur ?”")).toBeVisible();
    expect(screen.getByText("Voici une réponse mieux construite.")).toBeVisible();
    expect(screen.queryByText("To check")).toBeNull();
  });

  it("marks the improved answer “to check” with the terms the profile does not say", () => {
    show(makeInterview({ flags: ["Kubernetes", "Terraform"] }));
    expect(screen.getByText("To check")).toBeVisible();
    expect(screen.getByRole("note")).toHaveTextContent(
      "These terms aren't in your profile: Kubernetes, Terraform.",
    );
  });

  it("says how many revision cards were created and links to the revisions", () => {
    show(makeInterview({ cardsCreated: 3 }));
    expect(screen.getByText("3 review cards were created, to review tomorrow.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Open my reviews" })).toHaveAttribute(
      "href",
      "/study/reviews",
    );
  });

  it("says so when no card was created, with no link", () => {
    show(makeInterview({ cardsCreated: 0 }));
    expect(screen.getByText("No new review cards were created.")).toBeVisible();
    expect(screen.queryByRole("link", { name: "Open my reviews" })).toBeNull();
  });

  it("uses the singular for one card", () => {
    show(makeInterview({ cardsCreated: 1 }));
    expect(screen.getByText("1 review card was created, to review tomorrow.")).toBeVisible();
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
        "The answers to questions 1 and 3 couldn't be scored: " +
          "they don't count toward the scores.",
      ),
    ).toBeVisible();
    expect(screen.getAllByText("Not scored")).toHaveLength(2);
  });

  it("uses the singular for one unrated answer", () => {
    show(makeInterview({ debrief: makeDebrief({ unrated: [1] }) }));
    expect(
      screen.getByText(
        "The answer to question 2 couldn't be scored: it doesn't count toward the scores.",
      ),
    ).toBeVisible();
  });

  it("shows each answer with its note, and what a good answer would have said for a missed one", () => {
    show();
    const answers = within(screen.getByRole("region", { name: "Your answers" }));
    const second = within(answers.getByRole("article", { name: "Question 2" }));
    expect(second.getByText("Question 2 du recruteur ?")).toBeVisible();
    expect(second.getByText("Ma réponse 2.")).toBeVisible();
    expect(second.getByText("Score: 2 out of 5")).toBeVisible();
    expect(second.getByText("To review")).toBeVisible();
    expect(second.getByText("Citer le contexte")).toBeVisible();
    const first = within(answers.getByRole("article", { name: "Question 1" }));
    expect(first.getByText("Score: 4 out of 5")).toBeVisible();
    expect(first.queryByText("To review")).toBeNull();
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
