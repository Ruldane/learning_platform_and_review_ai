import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NumberField } from "./NumberField";

describe("NumberField", () => {
  it("says its bounds under the field and reports what is typed", async () => {
    const onChange = vi.fn();
    render(
      <NumberField label="Tours" value="3" min={1} max={5} invalid={false} onChange={onChange} />,
    );
    const field = screen.getByLabelText("Tours");
    expect(field).toHaveAccessibleDescription("Between 1 and 5.");
    expect(field).toHaveAttribute("aria-invalid", "false");
    await userEvent.setup().type(field, "4");
    expect(onChange).toHaveBeenCalledWith("34");
  });

  it("turns red, and names the field only, when it is invalid or refused by the server", () => {
    const { rerender } = render(
      <NumberField label="Tours" value="9" min={1} max={5} invalid onChange={vi.fn()} />,
    );
    expect(screen.getByLabelText("Tours")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Error: Between 1 and 5.")).toHaveClass("text-destructive");
    // l'état ne tient pas à la couleur seule : un mot, et le cadre du champ (variante aria-invalid)
    expect(screen.getByLabelText("Tours")).toHaveAccessibleDescription("Error: Between 1 and 5.");
    rerender(
      <NumberField
        label="Tours"
        value="3"
        min={1}
        max={5}
        invalid={false}
        refused
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Tours")).toHaveAccessibleDescription(
      "Error: The server refused this value: check it.",
    );
  });

  it("is also described by the extra message it is told about", () => {
    render(
      <>
        <p id="extra">Message commun.</p>
        <NumberField
          label="Tours"
          value="9"
          min={1}
          max={5}
          invalid
          describedBy="extra"
          onChange={vi.fn()}
        />
      </>,
    );
    expect(screen.getByLabelText("Tours")).toHaveAccessibleDescription(
      "Error: Between 1 and 5. Message commun.",
    );
  });

  it("shows a custom hint instead of the bounds", () => {
    render(
      <NumberField label="Plafond" value="1" hint="Au moins 10 000." invalid onChange={vi.fn()} />,
    );
    expect(screen.getByLabelText("Plafond")).toHaveAccessibleDescription(
      "Error: Au moins 10 000.",
    );
  });
});
