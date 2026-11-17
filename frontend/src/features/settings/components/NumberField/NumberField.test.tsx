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
    expect(field).toHaveAccessibleDescription("Entre 1 et 5.");
    expect(field).toHaveAttribute("aria-invalid", "false");
    await userEvent.setup().type(field, "4");
    expect(onChange).toHaveBeenCalledWith("34");
  });

  it("turns red, and names the field only, when it is invalid or refused by the server", () => {
    const { rerender } = render(
      <NumberField label="Tours" value="9" min={1} max={5} invalid onChange={vi.fn()} />,
    );
    expect(screen.getByLabelText("Tours")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Entre 1 et 5.")).toHaveClass("text-destructive");
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
      "Le serveur a refusé cette valeur : vérifie-la.",
    );
  });

  it("shows a custom hint instead of the bounds", () => {
    render(
      <NumberField label="Plafond" value="1" hint="Au moins 10 000." invalid onChange={vi.fn()} />,
    );
    expect(screen.getByLabelText("Plafond")).toHaveAccessibleDescription("Au moins 10 000.");
  });
});
