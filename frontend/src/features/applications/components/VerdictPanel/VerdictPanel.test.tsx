import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeVote, makeVotes } from "../fixtures";
import type { ChangeView, ObjectionView } from "../viewTypes";
import { VerdictPanel } from "./VerdictPanel";

const change = (over: Partial<ChangeView> = {}): ChangeView => ({
  text: "Chiffre le résultat de ton projet principal.",
  persona: "manager",
  needsSkill: false,
  terms: [],
  ...over,
});

const objections: ObjectionView[] = [
  { text: "Peu de résultats chiffrés.", personas: ["manager", "recruiter"] },
  { text: "Mot clé Kubernetes absent.", personas: ["ats_reader"] },
];

const section = (name: RegExp) => screen.getByRole("heading", { name }).parentElement!;

describe("VerdictPanel", () => {
  it("states the verdict in words with the vote count and its majority rule", () => {
    render(<VerdictPanel verdict="yes" votes={makeVotes()} objections={objections} changes={[]} />);
    expect(screen.getByText("The committee says:")).toBeVisible();
    expect(screen.getByText("Yes")).toBeVisible();
    expect(screen.getByText("At least 3 of the 4 readers voted yes.")).toBeVisible();
    expect(screen.getByText("The votes were 3 yes, 1 no, and 0 maybe.")).toBeVisible();
  });

  it("says that a split committee does not decide", () => {
    const votes = [
      makeVote({ persona: "ats_reader", vote: "yes" }),
      makeVote({ persona: "recruiter", vote: "yes" }),
      makeVote({ persona: "manager", vote: "no" }),
      makeVote({ persona: "colleague", vote: "no" }),
    ];
    render(<VerdictPanel verdict="maybe" votes={votes} objections={[]} changes={[]} />);
    expect(screen.getByText("Maybe")).toBeVisible();
    expect(
      screen.getByText("No answer got 3 votes out of 4: the committee can't decide."),
    ).toBeVisible();
    expect(screen.getByText("The votes were 2 yes, 2 no, and 0 maybe.")).toBeVisible();
  });

  it("explains a majority of maybe votes", () => {
    const votes = [
      makeVote({ persona: "ats_reader", vote: "maybe" }),
      makeVote({ persona: "recruiter", vote: "maybe" }),
      makeVote({ persona: "manager", vote: "maybe" }),
      makeVote({ persona: "colleague", vote: "no" }),
    ];
    render(<VerdictPanel verdict="maybe" votes={votes} objections={[]} changes={[]} />);
    expect(
      screen.getByText("At least 3 of the 4 readers voted maybe: the committee is hesitant."),
    ).toBeVisible();
    expect(screen.queryByText(/No answer got 3 votes/)).toBeNull();
    expect(screen.getByText("The votes were 0 yes, 1 no, and 3 maybe.")).toBeVisible();
  });

  it("ranks the objections and names who raised each", () => {
    render(<VerdictPanel verdict="yes" votes={makeVotes()} objections={objections} changes={[]} />);
    const items = within(section(/Objections, from most to least/)).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Peu de résultats chiffrés.");
    expect(items[0]).toHaveTextContent("Raised by: Manager, Recruiter");
    expect(items[1]).toHaveTextContent("Raised by: ATS reader");
  });

  it("labels skills to acquire in the suggested changes", () => {
    const changes = [
      change(),
      change({
        text: "À acquérir : Kubernetes. Ton profil ne le dit pas : ne l'écris pas dans ton CV.",
        persona: "ats_reader",
        needsSkill: true,
        terms: ["Kubernetes"],
      }),
      change({ text: "Resserre le résumé.", persona: "recruiter" }),
    ];
    render(<VerdictPanel verdict="yes" votes={makeVotes()} objections={[]} changes={changes} />);
    const items = within(section(/Three changes/)).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(within(items[0]!).queryByText("To acquire")).toBeNull();
    expect(within(items[1]!).getByText("To acquire")).toBeVisible();
    expect(within(items[1]!).getByText("Skills involved: Kubernetes")).toBeVisible();
    expect(items[1]).toHaveTextContent("ne l'écris pas dans ton CV");
    expect(items[1]).not.toHaveTextContent(/ajoute/i);
    expect(items[1]).toHaveTextContent("Suggested by: ATS reader");
  });

  it("marks an unsupported proper noun for review", () => {
    const changes = [
      change({
        text: "À vérifier : ton profil ne dit pas Capgemini. Ne l'écris pas dans ton CV.",
        needsSkill: true,
        terms: ["Capgemini"],
      }),
    ];
    render(<VerdictPanel verdict="yes" votes={makeVotes()} objections={[]} changes={changes} />);
    const [item] = within(section(/Three changes/)).getAllByRole("listitem");
    expect(within(item!).getByText("To check", { selector: "span" })).toBeVisible();
    expect(within(item!).queryByText("To acquire")).toBeNull();
    expect(within(item!).queryByText(/Skills involved/)).toBeNull();
  });

  it("gives its title a focus target for the page", () => {
    render(<VerdictPanel verdict="yes" votes={makeVotes()} objections={[]} changes={[]} />);
    expect(screen.getByRole("heading", { name: "Committee verdict" })).toHaveAttribute(
      "tabindex",
      "-1",
    );
  });
});
