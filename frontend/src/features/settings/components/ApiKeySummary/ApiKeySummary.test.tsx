import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ApiKeyEntry } from "../viewTypes";
import { ApiKeySummary } from "./ApiKeySummary";

const entry: ApiKeyEntry = {
  provider: "anthropic",
  label: "Anthropic",
  source: "ui",
  last4: "1234",
  readable: true,
  last_test_ok: true,
};

describe("ApiKeySummary", () => {
  it("affiche le fournisseur, les 4 derniers caractères et l'origine", () => {
    render(<ApiKeySummary entry={entry} headingId="titre" />);
    expect(screen.getByRole("heading", { name: "Anthropic" })).toHaveAttribute("id", "titre");
    expect(screen.getByText("•••• 1234")).toBeInTheDocument();
    expect(screen.getByText("saisie ici")).toBeInTheDocument();
    expect(screen.getByText("Dernier test : réussi")).toBeInTheDocument();
  });

  it("explique qu'une clé du fichier .env se retire de ce fichier", () => {
    render(<ApiKeySummary entry={{ ...entry, source: "env" }} headingId="titre" />);
    expect(screen.getByText("fichier .env")).toBeInTheDocument();
    expect(screen.getByText(/retire-la de ce fichier/)).toBeInTheDocument();
  });

  it("annonce l'absence de clé", () => {
    render(
      <ApiKeySummary
        entry={{ ...entry, source: null, last4: null, last_test_ok: null }}
        headingId="titre"
      />,
    );
    expect(screen.getByText("Aucune clé enregistrée")).toBeInTheDocument();
    expect(screen.queryByText(/Dernier test/)).not.toBeInTheDocument();
  });

  it("signale une clé illisible", () => {
    render(<ApiKeySummary entry={{ ...entry, readable: false }} headingId="titre" />);
    expect(screen.getByText("Clé illisible, ressaisis-la")).toBeInTheDocument();
  });
});
