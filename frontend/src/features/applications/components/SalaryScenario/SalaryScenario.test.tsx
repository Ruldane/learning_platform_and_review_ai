import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it } from "vitest";
import { SalaryScenario } from "./SalaryScenario";

it("sépare les montants du radar des règles et du bilan de la simulation", () => {
  render(
    <MemoryRouter>
      <SalaryScenario
        data={{
          runId: "r1",
          role: "Ingénieure IA",
          zone: "Lyon",
          minimum: 50000,
          maximum: 70000,
          observations: 2,
          outcome: { offer: 50000, remaining: 20000, reason: "budget_held" },
        }}
      />
    </MemoryRouter>,
  );
  const radar = screen.getByRole("region", { name: "Données du radar" });
  expect(radar).toHaveTextContent("50 000 € à 70 000 € bruts par an");
  expect(within(radar).getByRole("link", { name: "Consulter le relevé" })).toHaveAttribute(
    "href",
    "/carriere/radar/r1",
  );
  expect(screen.getByRole("region", { name: "Règles de la simulation" })).toBeVisible();
  const outcome = screen.getByRole("region", { name: "Bilan de la simulation" });
  expect(outcome).toHaveTextContent("20 000 €");
  expect(outcome).toHaveTextContent("Le recruteur simulé a maintenu l’offre d’ouverture.");
});
