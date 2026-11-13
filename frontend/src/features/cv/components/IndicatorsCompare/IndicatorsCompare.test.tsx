import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AtsCheckView, IndicatorsView } from "../viewTypes";
import { IndicatorsCompare } from "./IndicatorsCompare";

const checks = (headingsPassed: boolean): AtsCheckView[] => [
  { id: "selectable_text", passed: true, detail: "" },
  { id: "standard_headings", passed: headingsPassed, detail: "" },
];

const BEFORE: IndicatorsView = {
  coveragePercent: 58,
  covered: 7,
  total: 12,
  missing: ["Docker", "Kafka"],
  checks: checks(false),
};
const AFTER: IndicatorsView = {
  coveragePercent: 83,
  covered: 10,
  total: 12,
  missing: ["Kafka"],
  checks: checks(true),
};

describe("IndicatorsCompare", () => {
  it("compares the coverage and each check before and after", () => {
    render(<IndicatorsCompare before={BEFORE} after={AFTER} />);
    expect(screen.getByText("Couverture des exigences : 58 % → 83 %")).toBeInTheDocument();
    const row = screen.getByRole("row", { name: /Titres de sections standard/ });
    const cells = within(row).getAllByRole("cell");
    expect(cells.map((cell) => cell.textContent)).toEqual(["À revoir", "Réussi"]);
  });

  it("lists what is still missing after the generation", () => {
    render(<IndicatorsCompare before={BEFORE} after={AFTER} />);
    expect(screen.getByText("Kafka")).toBeInTheDocument();
    expect(screen.queryByText("Docker")).not.toBeInTheDocument();
  });

  it("shows the starting point only while there is no generated CV", () => {
    render(<IndicatorsCompare before={BEFORE} after={null} />);
    expect(screen.getByText("Couverture des exigences : 58 %")).toBeInTheDocument();
    expect(screen.getByText("Docker")).toBeInTheDocument();
    expect(screen.getAllByText("Pas encore")).toHaveLength(2);
  });

  it("says when every mandatory requirement is covered", () => {
    render(<IndicatorsCompare before={BEFORE} after={{ ...AFTER, missing: [] }} />);
    expect(
      screen.getByText("Toutes les exigences obligatoires sont couvertes."),
    ).toBeInTheDocument();
  });

  it("keeps the fixed guarantee mention", () => {
    render(<IndicatorsCompare before={BEFORE} after={AFTER} />);
    expect(screen.getByText(/Aucun outil ne garantit/)).toBeInTheDocument();
  });
});
