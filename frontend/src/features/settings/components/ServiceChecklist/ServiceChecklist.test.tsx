import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ServiceChecklist } from "./ServiceChecklist";

const report = {
  status: "degraded" as const,
  checks: {
    db: { ok: true, detail: "Disponible." },
    qdrant: { ok: false, detail: "Qdrant ne répond pas." },
    llm: { ok: false, detail: "Anthropic : aucune clé" },
    horloge: { ok: true, detail: "" },
  },
};

describe("ServiceChecklist", () => {
  it("writes the state of each service, in words", () => {
    render(<ServiceChecklist report={report} isLoading={false} isError={false} />);
    const list = screen.getByRole("list", { name: "État des services" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "Base de données : répond",
      "Mémoire vectorielle (Qdrant) : ne répond pas — Qdrant ne répond pas.",
      "Clé d'un modèle de langage : à configurer à l'étape 3",
      "horloge : répond",
    ]);
  });

  it("says it is checking while nothing has come back", () => {
    render(<ServiceChecklist isLoading isError={false} />);
    expect(screen.getByRole("status")).toHaveTextContent("Vérification des services…");
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("keeps one status zone from the start, empty until something is worth saying", () => {
    const { rerender } = render(<ServiceChecklist isLoading={false} isError={false} />);
    const zone = screen.getByRole("status");
    expect(zone).toBeEmptyDOMElement();
    rerender(<ServiceChecklist isLoading isError={false} />);
    expect(screen.getByRole("status")).toBe(zone);
    expect(zone).toHaveTextContent("Vérification des services…");
    rerender(<ServiceChecklist report={report} isLoading={false} isError />);
    expect(screen.getByRole("status")).toBe(zone);
    expect(zone).toHaveTextContent("Impossible de lire l'état des services");
    expect(screen.getAllByRole("status")).toHaveLength(1);
  });

  it("announces a service that comes back, in the same zone", () => {
    const down = { status: "degraded" as const, checks: { qdrant: report.checks.qdrant } };
    const up = { status: "ok" as const, checks: { qdrant: { ok: true, detail: "Disponible." } } };
    const { rerender } = render(
      <ServiceChecklist report={down} isLoading={false} isError={false} />,
    );
    const zone = screen.getByRole("status");
    expect(zone).toBeEmptyDOMElement();
    rerender(<ServiceChecklist report={up} isLoading={false} isError={false} />);
    expect(screen.getByRole("status")).toBe(zone);
    expect(zone).toHaveTextContent("Mémoire vectorielle (Qdrant) : répond de nouveau.");
  });

  it("says the server cannot be read, and keeps the last report it had", () => {
    const { rerender } = render(<ServiceChecklist isLoading={false} isError />);
    expect(screen.getByRole("status")).toHaveTextContent("Impossible de lire l'état des services");
    rerender(<ServiceChecklist report={report} isLoading={false} isError />);
    expect(screen.getByText("Base de données : répond")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("nouvel essai automatique");
  });
});
