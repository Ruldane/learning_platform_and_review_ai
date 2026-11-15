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
    render(<VerdictPanel verdict="oui" votes={makeVotes()} objections={objections} changes={[]} />);
    expect(screen.getByText("Le comité dit :")).toBeVisible();
    expect(screen.getByText("Oui")).toBeVisible();
    expect(screen.getByText("Au moins 3 des 4 lecteurs ont voté oui.")).toBeVisible();
    expect(screen.getByText("Les voix : 3 oui ; 1 non ; 0 peut-être.")).toBeVisible();
  });

  it("says that a split committee does not decide", () => {
    const votes = [
      makeVote({ persona: "ats_reader", vote: "oui" }),
      makeVote({ persona: "recruiter", vote: "oui" }),
      makeVote({ persona: "manager", vote: "non" }),
      makeVote({ persona: "colleague", vote: "non" }),
    ];
    render(<VerdictPanel verdict="peut_etre" votes={votes} objections={[]} changes={[]} />);
    expect(screen.getByText("Peut-être")).toBeVisible();
    expect(
      screen.getByText("Aucune réponse n'obtient 3 voix sur 4 : le comité ne tranche pas."),
    ).toBeVisible();
    expect(screen.getByText("Les voix : 2 oui ; 2 non ; 0 peut-être.")).toBeVisible();
  });

  it("says the committee hesitates, not that nobody has a majority, when three readers vote maybe", () => {
    const votes = [
      makeVote({ persona: "ats_reader", vote: "peut_etre" }),
      makeVote({ persona: "recruiter", vote: "peut_etre" }),
      makeVote({ persona: "manager", vote: "peut_etre" }),
      makeVote({ persona: "colleague", vote: "non" }),
    ];
    render(<VerdictPanel verdict="peut_etre" votes={votes} objections={[]} changes={[]} />);
    expect(
      screen.getByText("Au moins 3 des 4 lecteurs ont voté peut-être : le comité hésite."),
    ).toBeVisible();
    expect(screen.queryByText(/Aucune réponse n'obtient/)).toBeNull();
    expect(screen.getByText("Les voix : 0 oui ; 1 non ; 3 peut-être.")).toBeVisible();
  });

  it("ranks the objections and names who raised each", () => {
    render(<VerdictPanel verdict="oui" votes={makeVotes()} objections={objections} changes={[]} />);
    const items = within(section(/Objections, de la plus importante/)).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Peu de résultats chiffrés.");
    expect(items[0]).toHaveTextContent("Soulevée par : Manager, Recruteur");
    expect(items[1]).toHaveTextContent("Soulevée par : Lecteur ATS");
  });

  it("lists the changes and marks the ones that need a skill as « À acquérir », never as something to add", () => {
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
    render(<VerdictPanel verdict="oui" votes={makeVotes()} objections={[]} changes={changes} />);
    const items = within(section(/Trois changements/)).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(within(items[0]!).queryByText("À acquérir")).toBeNull();
    expect(within(items[1]!).getByText("À acquérir")).toBeVisible();
    expect(within(items[1]!).getByText("Compétences concernées : Kubernetes")).toBeVisible();
    expect(items[1]).toHaveTextContent("ne l'écris pas dans ton CV");
    expect(items[1]).not.toHaveTextContent(/ajoute/i);
    expect(items[1]).toHaveTextContent("Proposé par : Lecteur ATS");
  });

  it("marks a proper noun the profile does not say as « À vérifier », not as a skill to acquire", () => {
    const changes = [
      change({
        text: "À vérifier : ton profil ne dit pas Capgemini. Ne l'écris pas dans ton CV.",
        needsSkill: true,
        terms: ["Capgemini"],
      }),
    ];
    render(<VerdictPanel verdict="oui" votes={makeVotes()} objections={[]} changes={changes} />);
    const [item] = within(section(/Trois changements/)).getAllByRole("listitem");
    expect(within(item!).getByText("À vérifier", { selector: "span" })).toBeVisible();
    expect(within(item!).queryByText("À acquérir")).toBeNull();
    expect(within(item!).queryByText(/Compétences concernées/)).toBeNull();
  });

  it("gives its title a focus target for the page", () => {
    render(<VerdictPanel verdict="oui" votes={makeVotes()} objections={[]} changes={[]} />);
    expect(screen.getByRole("heading", { name: "Verdict du comité" })).toHaveAttribute(
      "tabindex",
      "-1",
    );
  });
});
