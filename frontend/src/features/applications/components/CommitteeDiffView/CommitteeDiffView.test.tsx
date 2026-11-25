import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CommitteeDiffView as DiffView } from "../viewTypes";
import { CommitteeDiffView } from "./CommitteeDiffView";

const diff: DiffView = {
  votes: [
    { persona: "ats_reader", before: "no", after: "yes" },
    { persona: "recruiter", before: "yes", after: "yes" },
    { persona: "manager", before: "yes", after: "maybe" },
    { persona: "colleague", before: "maybe", after: "yes" },
  ],
  resolved: ["Mot clé Kubernetes absent."],
  added: ["Résumé trop long."],
};

describe("CommitteeDiffView", () => {
  it("says there is nothing to compare for the first committee", () => {
    render(<CommitteeDiffView diff={null} />);
    expect(
      screen.getByText("This is the first committee for this posting: there's nothing to compare."),
    ).toBeVisible();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("compares each persona's vote before and after, the change written in words", () => {
    render(<CommitteeDiffView diff={diff} />);
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent(/ATS reader.*No.*Yes.*More favorable/);
    expect(rows[1]).toHaveTextContent(/Recruiter.*Yes.*Yes.*Unchanged/);
    expect(rows[2]).toHaveTextContent(/Manager.*Yes.*Maybe.*Less favorable/);
  });

  it("lists the objections that are gone and the new ones", () => {
    render(<CommitteeDiffView diff={diff} />);
    expect(screen.getByRole("heading", { name: "Objections resolved" })).toBeVisible();
    expect(screen.getByText("Mot clé Kubernetes absent.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "New objections" })).toBeVisible();
    expect(screen.getByText("Résumé trop long.")).toBeVisible();
  });

  it("says when no objection is gone or new", () => {
    render(<CommitteeDiffView diff={{ ...diff, resolved: [], added: [] }} />);
    expect(screen.getByText("No objections resolved.")).toBeVisible();
    expect(screen.getByText("No new objections.")).toBeVisible();
  });
});
