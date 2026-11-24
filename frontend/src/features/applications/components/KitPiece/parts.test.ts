import { describe, expect, it } from "vitest";
import { joinParts, splitParts } from "./parts";

describe("splitParts", () => {
  it("keeps a plain piece as one part without a label", () => {
    expect(splitParts("letter", "Bonjour,\n\nCordialement")).toEqual([
      { key: "text", label: null, text: "Bonjour,\n\nCordialement", blank: null },
    ]);
  });

  it("cuts the follow-ups at the --- line, 7 days first then 14 days", () => {
    const parts = splitParts("followups", "Relance 7\n\n---\n\nRelance 14");
    expect(parts.map((part) => [part.label, part.text])).toEqual([
      ["Follow-up after 7 days", "Relance 7"],
      ["Follow-up after 14 days", "Relance 14"],
    ]);
  });

  it("always offers both parts of a two-part piece, even when it is empty", () => {
    expect(splitParts("linkedin", "").map((part) => [part.label, part.text])).toEqual([
      ["Connection request", ""],
      ["Message after connecting", ""],
    ]);
    expect(splitParts("followups", "Seulement la première")).toHaveLength(2);
  });

  it("makes one part per form question and empties the blanks the code left", () => {
    const parts = splitParts(
      "form_answers",
      "### Pourquoi nous ?\nParce que.\n\n### Prétentions salariales ?\nÀ remplir par toi\n\n### Votre Kubernetes ?\nÀ compléter",
    );
    expect(parts.map((part) => [part.label, part.text, part.blank])).toEqual([
      ["Pourquoi nous ?", "Parce que.", null],
      ["Prétentions salariales ?", "", "salary"],
      ["Votre Kubernetes ?", "", "complete"],
    ]);
  });

  it("shows a form without any question as one plain part", () => {
    expect(
      splitParts("form_answers", "Aucune question éliminatoire repérée dans l'offre."),
    ).toEqual([
      {
        key: "text",
        label: null,
        text: "Aucune question éliminatoire repérée dans l'offre.",
        blank: null,
      },
    ]);
  });
});

describe("joinParts", () => {
  it("gives back what splitParts read", () => {
    const followups = "Relance 7\n\n---\n\nRelance 14";
    expect(joinParts("followups", splitParts("followups", followups))).toBe(followups);
    for (const blank of ["For you to fill in", "À remplir par toi"]) {
      const form = `### Pourquoi nous ?\nParce que.\n\n### Prétentions ?\n${blank}`;
      expect(splitParts("form_answers", form)[1]?.blank).toBe("salary");
      expect(joinParts("form_answers", splitParts("form_answers", form))).toBe(form);
    }
  });

  it("puts a blank marker back for an empty form answer, and nothing for an empty piece", () => {
    const parts = splitParts(
      "form_answers",
      "### Prétentions ?\nÀ remplir par toi\n\n### Autre ?\nOui",
    );
    const emptied = parts.map((part) => (part.key === "q1" ? { ...part, text: "" } : part));
    expect(joinParts("form_answers", emptied)).toBe(
      "### Prétentions ?\nÀ remplir par toi\n\n### Autre ?\nTo complete",
    );
    expect(joinParts("followups", splitParts("followups", ""))).toBe("");
    expect(joinParts("letter", [{ key: "text", label: null, text: "", blank: null }])).toBe("");
  });
});
