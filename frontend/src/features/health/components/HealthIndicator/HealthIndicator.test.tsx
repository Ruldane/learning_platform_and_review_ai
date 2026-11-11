import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HealthIndicator } from "./HealthIndicator";

describe("HealthIndicator", () => {
  it("liste les services en échec", () => {
    render(
      <HealthIndicator
        isLoading={false}
        report={{
          status: "degraded",
          checks: {
            ollama: { ok: false, detail: "Le modèle bge-m3 est en cours de téléchargement." },
            qdrant: { ok: true, detail: "Qdrant répond." },
          },
        }}
      />,
    );
    expect(screen.getByText(/bge-m3/)).toBeInTheDocument();
    expect(screen.queryByText(/Qdrant répond/)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Certains services ne répondent pas");
  });

  it("affiche l'état nominal", () => {
    render(<HealthIndicator isLoading={false} report={{ status: "ok", checks: {} }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Tous les services répondent");
  });

  it("affiche la base indisponible", () => {
    render(
      <HealthIndicator
        isLoading={false}
        report={{ status: "down", checks: { database: { ok: false, detail: "Base fermée." } } }}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Base de données indisponible");
  });

  it("affiche un état neutre pendant le chargement", () => {
    render(<HealthIndicator isLoading />);
    expect(screen.getByRole("status")).toHaveTextContent("Vérification des services…");
  });

  it("affiche serveur injoignable en cas d'erreur de requête", () => {
    render(<HealthIndicator isLoading={false} isError />);
    expect(screen.getByRole("status")).toHaveTextContent("Serveur injoignable");
  });
});
