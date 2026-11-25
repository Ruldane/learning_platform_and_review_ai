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
    const items = within(
      screen.getByRole("list", { name: "Result for each criterion" }),
    ).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Ventes agrégées par mois");
    expect(items[0]).toHaveTextContent("Met");
    expect(items[0]).toHaveTextContent("La requête groupe bien par mois.");
    expect(items[1]).toHaveTextContent("Not met");
    expect(items[1]).toHaveTextContent("Aucun test trouvé.");
    expect(items[2]).toHaveTextContent("Met");
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
    expect(screen.getAllByText("Not reviewed yet")).toHaveLength(3);
    rerender(
      <CriteriaChecklist criteria={CRITERIA} results={[{ index: 2, met: true, comment: "" }]} />,
    );
    expect(screen.getAllByText("Not reviewed yet")).toHaveLength(2);
    expect(screen.getAllByText("Met")).toHaveLength(1);
  });

  it("matches results by their index, whatever their order, and ignores an index outside the criteria", () => {
    render(
      <CriteriaChecklist
        criteria={CRITERIA}
        results={[
          { index: 3, met: false, comment: "README absent." },
          { index: 9, met: true, comment: "Hors critères." },
          { index: 1, met: true, comment: "Requête correcte." },
        ]}
      />,
    );
    const items = within(
      screen.getByRole("list", { name: "Result for each criterion" }),
    ).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("Ventes agrégées par mois");
    expect(items[0]).toHaveTextContent("Requête correcte.");
    expect(items[1]).toHaveTextContent("Not reviewed yet");
    expect(items[2]).toHaveTextContent("README clair");
    expect(items[2]).toHaveTextContent("Not met");
    expect(items[2]).toHaveTextContent("README absent.");
    expect(screen.queryByText("Hors critères.")).toBeNull();
  });
});
