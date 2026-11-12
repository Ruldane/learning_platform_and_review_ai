import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CompareRowView } from "../viewTypes";
import { CompareTable } from "./CompareTable";

const rows: CompareRowView[] = [
  { skillId: "s1", name: "HTML", domain: "web", mine: "valide", target: "valide", gap: 0 },
  { skillId: "s2", name: "React", domain: "web", mine: "declare", target: "valide", gap: 2 },
  { skillId: "s3", name: "SQL", domain: "données", mine: null, target: "valide", gap: 4 },
];

function bodyRows() {
  return within(screen.getByRole("table")).getAllByRole("row").slice(1);
}

describe("CompareTable", () => {
  it("shows gaps and coverage", () => {
    render(<CompareTable rows={rows} coverage={33} targetLabel="Développeuse front" />);
    expect(screen.getByText("Cible : Développeuse front")).toBeInTheDocument();
    expect(screen.getByText("Couverture : 33 %")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Part des compétences cibles atteintes" });
    expect(bar).toHaveAttribute("aria-valuenow", "33");
    expect(screen.getByRole("table", { name: "Comparaison avec le poste cible" })).toBeVisible();
    const cells = bodyRows().map((row) =>
      within(row)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    );
    expect(cells).toEqual([
      ["SQL", "données", "Absent", "Validé", "Manque 4 niveaux"],
      ["React", "web", "Déclaré", "Validé", "Manque 2 niveaux"],
      ["HTML", "web", "Validé", "Validé", "Atteint"],
    ]);
  });

  it("uses the singular for a gap of one level", () => {
    const row: CompareRowView = { ...rows[1]!, mine: "en_cours", gap: 1 };
    render(<CompareTable rows={[row]} coverage={0} targetLabel="Cible" />);
    expect(screen.getByText("Manque 1 niveau")).toBeInTheDocument();
  });

  it("lists the biggest gaps first, keeping the given order between equal gaps", () => {
    const tie: CompareRowView = { ...rows[1]!, skillId: "s4", name: "Vue" };
    render(
      <CompareTable rows={[rows[0]!, rows[1]!, tie, rows[2]!]} coverage={25} targetLabel="C" />,
    );
    const names = bodyRows().map((row) => within(row).getAllByRole("cell")[0]!.textContent);
    expect(names).toEqual(["SQL", "React", "Vue", "HTML"]);
  });

  it("says when there is nothing to compare", () => {
    render(<CompareTable rows={[]} coverage={0} targetLabel="Cible" />);
    expect(screen.getByText("Aucune compétence à comparer")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });
});
