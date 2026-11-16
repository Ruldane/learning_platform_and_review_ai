import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CriteriaChecklist } from "./CriteriaChecklist";

const CRITERIA = ["Ventes agrégées par mois", "Un test vérifie le total", "README clair"];

describe("CriteriaChecklist", () => {
  it("writes « Atteint » or « Non atteint » for each criterion, with the comment", () => {
    render(
      <CriteriaChecklist
        criteria={CRITERIA}
        results={[
          { index: 1, met: true, comment: "La requête groupe bien par mois." },
          { index: 2, met: false, comment: "Aucun test trouvé." },
          { index: 3, met: true, comment: "" },
        ]}
      />,
    );
    const items = within(screen.getByRole("list", { name: "Critères de réussite" })).getAllByRole(
      "listitem",
    );
    expect(items[0]).toHaveTextContent("Ventes agrégées par mois");
    expect(items[0]).toHaveTextContent("Atteint");
    expect(items[0]).toHaveTextContent("La requête groupe bien par mois.");
    expect(items[1]).toHaveTextContent("Non atteint");
    expect(items[1]).toHaveTextContent("Aucun test trouvé.");
    expect(items[2]).toHaveTextContent("Atteint");
  });

  it("never relies on the icons: they are hidden from assistive technology", () => {
    const { container } = render(
      <CriteriaChecklist criteria={CRITERIA} results={[{ index: 1, met: true, comment: "" }]} />,
    );
    const icons = container.querySelectorAll("svg");
    expect(icons).toHaveLength(3);
    icons.forEach((icon) => expect(icon).toHaveAttribute("aria-hidden", "true"));
  });

  it("says a criterion is not evaluated yet when there are no results or no result for it", () => {
    const { rerender } = render(<CriteriaChecklist criteria={CRITERIA} results={null} />);
    expect(screen.getAllByText("Pas encore évalué")).toHaveLength(3);
    rerender(
      <CriteriaChecklist criteria={CRITERIA} results={[{ index: 2, met: true, comment: "" }]} />,
    );
    expect(screen.getAllByText("Pas encore évalué")).toHaveLength(2);
    expect(screen.getAllByText("Atteint")).toHaveLength(1);
  });
});
