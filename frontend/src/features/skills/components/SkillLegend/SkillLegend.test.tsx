import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LEVEL_COLORS } from "../levels";
import { SkillLegend } from "./SkillLegend";

describe("SkillLegend", () => {
  it("names each level in words next to its color", () => {
    render(<SkillLegend />);
    const list = screen.getByRole("list", { name: "Légende des niveaux" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "Absent",
      "Déclaré",
      "En cours",
      "Validé",
      "Prouvé",
    ]);
    const swatch = items[3]!.querySelector("[data-swatch]");
    expect(swatch).toHaveStyle({ backgroundColor: LEVEL_COLORS.valide });
  });

  it("explains what color and size mean", () => {
    render(<SkillLegend />);
    expect(screen.getByText("Couleur : niveau de maîtrise.")).toBeInTheDocument();
    expect(screen.getByText(/Taille : demande du marché/)).toBeInTheDocument();
  });
});
