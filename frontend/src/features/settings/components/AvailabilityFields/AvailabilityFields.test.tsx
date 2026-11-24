import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AvailabilityFields } from "./AvailabilityFields";

const values = { weekday: "120", weekendMin: "180", weekendMax: "240" };
const ok = { weekday: false, weekendMin: false, weekendMax: false, weekendOrder: false };
const WEEKDAY = "Minutes per day, Monday to Friday";
const WEEKEND_MIN = "Weekend block, minimum (minutes)";
const WEEKEND_MAX = "Weekend block, maximum (minutes)";
const ORDER_ERROR = "Error: The weekend minimum must stay less than or equal to its maximum.";

describe("AvailabilityFields", () => {
  it("shows the computed weekly budget", () => {
    render(<AvailabilityFields values={values} flags={ok} budget={840} onChange={vi.fn()} />);
    expect(screen.getByText("Weekly budget: 14 h")).toBeInTheDocument();
    expect(screen.getByText("Five weekdays plus the longest weekend block.")).toBeInTheDocument();
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
      screen.getByText("Weekly budget: fix the durations above."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(WEEKDAY)).toHaveAttribute("aria-invalid", "true");
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
    const error = screen.getByText(ORDER_ERROR);
    // le message est relié aux deux champs qu'il concerne, en plus de leur propre aide
    for (const name of [WEEKEND_MIN, WEEKEND_MAX]) {
      expect(screen.getByLabelText(name).getAttribute("aria-describedby")).toContain(error.id);
    }
    expect(screen.getByLabelText(WEEKDAY)).toHaveAccessibleDescription("Between 0 and 1440.");
    await userEvent.setup().type(screen.getByLabelText(WEEKEND_MAX), "5");
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
    for (const name of [WEEKEND_MIN, WEEKEND_MAX]) {
      expect(screen.getByLabelText(name)).toHaveAttribute("aria-invalid", "true");
      expect(screen.getByLabelText(name)).toHaveAccessibleDescription(
        `Between 0 and 1440. ${ORDER_ERROR}`,
      );
    }
  });

  it("labels an out-of-bounds value as an error", () => {
    render(
      <AvailabilityFields
        values={{ ...values, weekday: "2000" }}
        flags={{ ...ok, weekday: true }}
        budget={null}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText(WEEKDAY)).toHaveAccessibleDescription(
      "Error: Between 0 and 1440.",
    );
  });
});
