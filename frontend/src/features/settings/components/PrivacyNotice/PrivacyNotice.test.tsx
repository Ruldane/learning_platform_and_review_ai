import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PrivacyNotice } from "./PrivacyNotice";

describe("PrivacyNotice", () => {
  it("lists what leaves the machine, and where it goes (17.3)", () => {
    render(<PrivacyNotice />);
    const table = screen.getByRole("table", { name: "Ce qui sort de ta machine" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(
      rows.map((row) =>
        within(row)
          .getAllByRole("cell")
          .map((c) => c.textContent),
      ),
    ).toEqual([
      [
        "Les prompts, qui peuvent contenir ton CV et ton profil",
        "Le fournisseur de modèle que tu choisis",
      ],
      ["Les requêtes de recherche", "Les moteurs interrogés par SearXNG"],
      ["Tout le reste (base, vecteurs, fichiers, embeddings)", "Reste sur ta machine"],
    ]);
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((c) => c.textContent),
    ).toEqual(["Donnée", "Destination"]);
  });

  it("says what is removed from searches and what contacts keep", () => {
    render(<PrivacyNotice />);
    expect(
      screen.getByText(/retire ton nom, ton e-mail et ton téléphone des requêtes/),
    ).toBeInTheDocument();
    expect(screen.getByText(/se limitent au nom, au rôle et à un lien public/)).toBeInTheDocument();
    expect(screen.getByText(/tout exporter ou tout supprimer/)).toBeInTheDocument();
  });
});
