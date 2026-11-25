import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ComparisonBody } from "./ComparisonBody";

describe("Comparaison d’une vérification IDE", () => {
  it("indique l’étape en cours à côté des seuls repères connus du fantôme", () => {
    render(
      <ComparisonBody
        kind="ide"
        selected={{
          id: "check-1",
          at: "2026-11-22T10:00:00Z",
          version: "same",
          metrics: { duration: 1800, errors: 0, completed: 1, total: 1 },
        }}
        current={null}
        ongoing
      />,
    );
    expect(screen.getByRole("heading", { name: "Your current attempt" })).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Checking");
    expect(screen.queryByRole("timer")).toBeNull();
    expect(screen.getAllByText("Check duration")).toHaveLength(1);
  });
});
