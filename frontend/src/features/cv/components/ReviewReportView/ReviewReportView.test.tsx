import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { ReportView } from "../viewTypes";
import { ReviewReportView } from "./ReviewReportView";

const REPORT: ReportView = {
  ats: "Greenhouse",
  atsNotes: ["Un seul fichier PDF, texte sélectionnable."],
  companySummary: "Société Fictive édite un logiciel de paie.",
  strengths: ["Cinq ans d'expérience en Python."],
  risks: ["Peu d'expérience du cloud."],
  eliminatory: ["Permis B exigé."],
};

function setup(report: ReportView = REPORT, gapTerms: string[] = ["AWS"]) {
  render(
    <MemoryRouter>
      <ReviewReportView report={report} gapTerms={gapTerms} gapHref="/carriere/ecarts/p1" />
    </MemoryRouter>,
  );
}

describe("ReviewReportView", () => {
  it("shows strengths, risks and eliminatory criteria in their own lists", () => {
    setup();
    for (const [title, text] of [
      ["Forces", "Cinq ans d'expérience en Python."],
      ["Risques", "Peu d'expérience du cloud."],
      ["Critères éliminatoires", "Permis B exigé."],
    ] as const) {
      const section = screen
        .getByRole("heading", { name: title })
        .closest("section") as HTMLElement;
      expect(within(section).getByText(text)).toBeInTheDocument();
    }
  });

  it("shows the detected recruiting software and the company sheet", () => {
    setup();
    expect(screen.getByText("Logiciel de recrutement détecté : Greenhouse")).toBeInTheDocument();
    expect(screen.getByText("Un seul fichier PDF, texte sélectionnable.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Fiche entreprise" })).toBeInTheDocument();
    expect(screen.getByText("Société Fictive édite un logiciel de paie.")).toBeInTheDocument();
  });

  it("gap terms label", () => {
    setup(REPORT, ["AWS", "Kafka"]);
    expect(
      screen.getByText(/Mots clés de l'offre à appuyer par un fait ou à acquérir : AWS, Kafka/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voir l'écart" })).toHaveAttribute(
      "href",
      "/carriere/ecarts/p1",
    );
  });

  it("omits the gap line, the company sheet and the notes when there is nothing", () => {
    setup({ ...REPORT, ats: null, atsNotes: [], companySummary: null, strengths: [] }, []);
    expect(screen.getByText("Logiciel de recrutement non détecté.")).toBeInTheDocument();
    expect(screen.queryByText(/Mots clés de l'offre absents/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Fiche entreprise" })).not.toBeInTheDocument();
    const section = screen
      .getByRole("heading", { name: "Forces" })
      .closest("section") as HTMLElement;
    expect(within(section).getByText("Rien à signaler.")).toBeInTheDocument();
  });

  it("renders everything as plain text", () => {
    setup({ ...REPORT, strengths: ["<img src=x onerror=alert(1)>"] });
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
});
