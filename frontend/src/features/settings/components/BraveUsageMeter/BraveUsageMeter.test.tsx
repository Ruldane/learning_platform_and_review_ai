import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BraveUsageMeter } from "./BraveUsageMeter";

describe("BraveUsageMeter", () => {
  it("montre le compte du mois", () => {
    render(<BraveUsageMeter usage={{ hasKey: true, used: 312, cap: 900, month: "2026-11" }} />);
    expect(screen.getByText("312 / 900 requêtes en novembre 2026")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Requêtes Brave du mois" });
    expect(bar).toHaveAttribute("aria-valuenow", "312");
    expect(bar).toHaveAttribute("aria-valuemax", "900");
  });

  it("annonce le plafond atteint", () => {
    render(<BraveUsageMeter usage={{ hasKey: true, used: 900, cap: 900, month: "2026-11" }} />);
    expect(screen.getByText(/plafond du mois est atteint/i)).toBeInTheDocument();
  });

  it("n'affiche pas d'alerte sous le plafond", () => {
    render(<BraveUsageMeter usage={{ hasKey: true, used: 0, cap: 900, month: "2026-11" }} />);
    expect(screen.queryByText(/plafond du mois est atteint/i)).not.toBeInTheDocument();
  });

  it("dit que Brave est inactif sans clé, sans jauge", () => {
    render(<BraveUsageMeter usage={{ hasKey: false, used: 0, cap: 900, month: "2026-11" }} />);
    expect(screen.getByText("Brave inactif (aucune clé)")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("garde le texte brut d'un mois illisible", () => {
    render(<BraveUsageMeter usage={{ hasKey: true, used: 1, cap: 900, month: "bientôt" }} />);
    expect(screen.getByText("1 / 900 requêtes en bientôt")).toBeInTheDocument();
  });
});
