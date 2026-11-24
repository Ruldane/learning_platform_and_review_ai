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
      <ReviewReportView report={report} gapTerms={gapTerms} gapHref="/career/postings/p1" />
    </MemoryRouter>,
  );
}

describe("ReviewReportView", () => {
  it("shows strengths, risks and eliminatory criteria in their own lists", () => {
    setup();
    for (const [title, text] of [
      ["Strengths", "Cinq ans d'expérience en Python."],
      ["Risks", "Peu d'expérience du cloud."],
      ["Deal-breakers", "Permis B exigé."],
    ] as const) {
      const section = screen
        .getByRole("heading", { name: title })
        .closest("section") as HTMLElement;
      expect(within(section).getByText(text)).toBeInTheDocument();
    }
  });

  it("shows the detected recruiting software and the company sheet", () => {
    setup();
    expect(screen.getByText("Applicant tracking system detected: Greenhouse")).toBeInTheDocument();
    expect(screen.getByText("Un seul fichier PDF, texte sélectionnable.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Company profile" })).toBeInTheDocument();
    expect(screen.getByText("Société Fictive édite un logiciel de paie.")).toBeInTheDocument();
  });

  it("gap terms label", () => {
    setup(REPORT, ["AWS", "Kafka"]);
    expect(
      screen.getByText(/Posting keywords to back up with a fact or to acquire: AWS, Kafka/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View the gap" })).toHaveAttribute(
      "href",
      "/career/postings/p1",
    );
  });

  it("omits the gap line, the company sheet and the notes when there is nothing", () => {
    setup({ ...REPORT, ats: null, atsNotes: [], companySummary: null, strengths: [] }, []);
    expect(screen.getByText("No applicant tracking system detected.")).toBeInTheDocument();
    expect(screen.queryByText(/Posting keywords to back up/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Company profile" })).not.toBeInTheDocument();
    const section = screen
      .getByRole("heading", { name: "Strengths" })
      .closest("section") as HTMLElement;
    expect(within(section).getByText("Nothing to report.")).toBeInTheDocument();
  });

  it("renders everything as plain text", () => {
    setup({ ...REPORT, strengths: ["<img src=x onerror=alert(1)>"] });
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
});
