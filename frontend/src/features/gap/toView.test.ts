import { describe, expect, it } from "vitest";
import {
  certainDuplicate,
  toAnalysisView,
  toGapRows,
  toMissingViews,
  toPostingListItems,
} from "./toView";

describe("toView", () => {
  it("reduces the analysis to the card's fields", () => {
    const view = toAnalysisView({
      apply_url: null,
      company: "Société Fictive",
      eliminatory: [{ kind: "language", text: "Anglais courant" }],
      keywords: [{ term: "Kubernetes", variants: ["K8s"] }],
      language: "fr",
      level: "senior",
      location: "Lyon",
      remote: "partiel",
      requirements: [{ required: true, skills: ["Python"], text: "Python solide" }],
      skills: [{ domain: null, learnable: true, name: "Python", required: true }],
      title: "Ingénieure données",
      tools: ["Airflow"],
    });
    expect(view).toEqual({
      title: "Ingénieure données",
      company: "Société Fictive",
      level: "senior",
      location: "Lyon",
      remote: "partiel",
      requirements: [{ text: "Python solide", required: true }],
      keywords: ["Kubernetes"],
      eliminatory: ["Anglais courant"],
      tools: ["Airflow"],
    });
  });

  it("keeps the source and the week of a gap row", () => {
    expect(
      toGapRows([
        {
          action: "in_program",
          level: null,
          required: true,
          skill: "SQL",
          source: "posting",
          week: 3,
        },
        {
          action: "to_add",
          level: "declared",
          required: false,
          skill: "Kafka",
          source: "cv_review",
          week: null,
        },
      ]),
    ).toEqual([
      {
        action: "in_program",
        level: null,
        required: true,
        skill: "SQL",
        source: "posting",
        week: 3,
      },
      {
        action: "to_add",
        level: "declared",
        required: false,
        skill: "Kafka",
        source: "cv_review",
        week: null,
      },
    ]);
  });

  it("renames required_in and keeps the order", () => {
    expect(
      toMissingViews([
        { skill: "Python", postings: 5, required_in: 4 },
        { skill: "Go", postings: 1, required_in: 0 },
      ]),
    ).toEqual([
      { skill: "Python", postings: 5, requiredIn: 4 },
      { skill: "Go", postings: 1, requiredIn: 0 },
    ]);
  });

  it("builds list items and a certain duplicate", () => {
    const summary = {
      id: "p1",
      title: null,
      company: null,
      score: null,
      status: "analyzing" as const,
      source: "url" as const,
      has_review: false,
      created_at: "2026-11-03T10:00:00Z",
    };
    expect(toPostingListItems([summary])).toEqual([
      { id: "p1", title: null, company: null, score: null, status: "analyzing" },
    ]);
    expect(certainDuplicate(summary)).toEqual({
      level: "certain",
      postingId: "p1",
      title: null,
      company: null,
      createdAt: "2026-11-03T10:00:00Z",
    });
  });
});
