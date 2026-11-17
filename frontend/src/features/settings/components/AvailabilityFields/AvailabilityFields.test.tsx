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

  it("reports which duration changed, and says when the weekend block is out of order", async () => {
    const onChange = vi.fn();
    render(
      <AvailabilityFields
        values={values}
        flags={{ ...ok, weekendMin: true, weekendMax: true, weekendOrder: true }}
        budget={840}
        onChange={onChange}
      />,
    );
    expect(
      screen.getByText("Le minimum du week-end ne dépasse pas son maximum."),
    ).toBeInTheDocument();
    await userEvent.setup().type(screen.getByLabelText("Bloc du week-end, maximum (minutes)"), "5");
    expect(onChange).toHaveBeenCalledWith("weekendMax", "2405");
  });
});
