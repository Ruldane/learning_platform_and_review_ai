import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AvailabilityFields } from "./AvailabilityFields";

const values = { weekday: "120", weekendMin: "180", weekendMax: "240" };
const ok = { weekday: false, weekendMin: false, weekendMax: false, weekendOrder: false };

describe("AvailabilityFields", () => {
  it("shows the computed weekly budget", () => {
    render(<AvailabilityFields values={values} flags={ok} budget={840} onChange={vi.fn()} />);
    expect(screen.getByText("Budget hebdomadaire : 14 h")).toBeInTheDocument();
    expect(screen.getByText(/Cinq jours de semaine/)).toBeInTheDocument();
  });

  it("asks to fix the durations instead of showing a budget that means nothing", () => {
    render(
      <AvailabilityFields
        values={{ ...values, weekday: "" }}
        flags={{ ...ok, weekday: true }}
        budget={null}
        onChange={vi.fn()}
      />,
    );
    expect(
      screen.getByText("Budget hebdomadaire : corrige les durées ci-dessus."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Minutes par jour, du lundi au vendredi")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("reports which duration changed, and says when the weekend block is inverted", async () => {
    const onChange = vi.fn();
    render(
      <AvailabilityFields
        values={values}
        flags={{ ...ok, weekendMin: true, weekendMax: true, weekendOrder: true }}
        budget={840}
        onChange={onChange}
      />,
    );
    const order = "Erreur : Le minimum du week-end doit rester inférieur ou égal à son maximum.";
    expect(screen.getByText(order)).toBeInTheDocument();
    // le message est relié aux deux champs qu'il concerne, en plus de leur propre aide
    for (const name of [
      "Bloc du week-end, minimum (minutes)",
      "Bloc du week-end, maximum (minutes)",
    ]) {
      expect(screen.getByLabelText(name).getAttribute("aria-describedby")).toContain(
        screen.getByText(order).id,
      );
    }
    expect(
      screen.getByLabelText("Minutes par jour, du lundi au vendredi"),
    ).toHaveAccessibleDescription("Entre 0 et 1440.");
    await userEvent.setup().type(screen.getByLabelText("Bloc du week-end, maximum (minutes)"), "5");
    expect(onChange).toHaveBeenCalledWith("weekendMax", "2405");
  });

  it("does not call a value in bounds an error: only the order message does", () => {
    render(
      <AvailabilityFields
        values={{ ...values, weekendMin: "500", weekendMax: "240" }}
        flags={{ ...ok, weekendMin: true, weekendMax: true, weekendOrder: true }}
        budget={840}
        onChange={vi.fn()}
      />,
    );
    const order = "Erreur : Le minimum du week-end doit rester inférieur ou égal à son maximum.";
    for (const name of [
      "Bloc du week-end, minimum (minutes)",
      "Bloc du week-end, maximum (minutes)",
    ]) {
      expect(screen.getByLabelText(name)).toHaveAttribute("aria-invalid", "true");
      expect(screen.getByLabelText(name)).toHaveAccessibleDescription(`Entre 0 et 1440. ${order}`);
    }
  });

  it("still says « Erreur » on a value that is out of bounds", () => {
    render(
      <AvailabilityFields
        values={{ ...values, weekday: "2000" }}
        flags={{ ...ok, weekday: true }}
        budget={null}
        onChange={vi.fn()}
      />,
    );
    expect(
      screen.getByLabelText("Minutes par jour, du lundi au vendredi"),
    ).toHaveAccessibleDescription("Erreur : Entre 0 et 1440.");
  });
});
