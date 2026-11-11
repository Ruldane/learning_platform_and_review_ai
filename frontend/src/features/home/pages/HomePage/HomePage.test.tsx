import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomePage } from "./HomePage";

describe("HomePage", () => {
  it("affiche le titre, l'introduction et un état vide", () => {
    render(<HomePage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Bienvenue sur Tremplin" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Ta plateforme locale d'apprentissage et de carrière.")).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Ton brief du jour arrivera bientôt" }),
    ).toBeInTheDocument();
  });
});
