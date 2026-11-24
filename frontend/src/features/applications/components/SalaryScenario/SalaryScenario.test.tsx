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
  const radar = screen.getByRole("region", { name: "Radar data" });
  expect(radar).toHaveTextContent("€50,000 to €70,000 gross per year");
  expect(within(radar).getByRole("link", { name: "View the snapshot" })).toHaveAttribute(
    "href",
    "/career/radar/r1",
  );
  expect(screen.getByRole("region", { name: "Simulation rules" })).toBeVisible();
  const outcome = screen.getByRole("region", { name: "Simulation summary" });
  expect(outcome).toHaveTextContent("€20,000");
  expect(outcome).toHaveTextContent("The simulated recruiter held to the opening offer.");
});
