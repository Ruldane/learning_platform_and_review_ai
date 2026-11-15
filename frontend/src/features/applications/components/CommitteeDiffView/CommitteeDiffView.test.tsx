import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CommitteeDiffView as DiffView } from "../viewTypes";
import { CommitteeDiffView } from "./CommitteeDiffView";

const diff: DiffView = {
  votes: [
    { persona: "ats_reader", before: "non", after: "oui" },
    { persona: "recruiter", before: "oui", after: "oui" },
    { persona: "manager", before: "oui", after: "peut_etre" },
    { persona: "colleague", before: "peut_etre", after: "oui" },
  ],
  resolved: ["Mot clé Kubernetes absent."],
  added: ["Résumé trop long."],
};

describe("CommitteeDiffView", () => {
  it("says there is nothing to compare for the first committee", () => {
    render(<CommitteeDiffView diff={null} />);
    expect(
      screen.getByText("C'est le premier comité pour cette offre : il n'y a rien à comparer."),
    ).toBeVisible();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("compares each persona's vote before and after, the change written in words", () => {
    render(<CommitteeDiffView diff={diff} />);
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent(/Lecteur ATS.*Non.*Oui.*Plus favorable/);
    expect(rows[1]).toHaveTextContent(/Recruteur.*Oui.*Oui.*Inchangé/);
    expect(rows[2]).toHaveTextContent(/Manager.*Oui.*Peut-être.*Moins favorable/);
  });

  it("lists the objections that are gone and the new ones", () => {
    render(<CommitteeDiffView diff={diff} />);
    expect(screen.getByRole("heading", { name: "Objections levées" })).toBeVisible();
    expect(screen.getByText("Mot clé Kubernetes absent.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Nouvelles objections" })).toBeVisible();
    expect(screen.getByText("Résumé trop long.")).toBeVisible();
  });

  it("says when no objection is gone or new", () => {
    render(<CommitteeDiffView diff={{ ...diff, resolved: [], added: [] }} />);
    expect(screen.getByText("Aucune objection levée.")).toBeVisible();
    expect(screen.getByText("Aucune nouvelle objection.")).toBeVisible();
  });
});
