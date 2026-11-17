import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DelaysField } from "./DelaysField";

describe("DelaysField", () => {
  it("shows the three delays in a named group and reports the one that changed", async () => {
    const onChange = vi.fn();
    render(<DelaysField value={["7", "14", "21"]} invalid={false} onChange={onChange} />);
    expect(screen.getByRole("group", { name: /Délais de relance/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Première relance")).toHaveValue(7);
    expect(screen.getByLabelText("Troisième relance")).toHaveValue(21);
    await userEvent.setup().type(screen.getByLabelText("Deuxième relance"), "5");
    expect(onChange).toHaveBeenCalledWith(1, "145");
  });

  it("says the rule, in red when it is broken, and when the server refused it", () => {
    const { rerender } = render(
      <DelaysField value={["7", "7", "21"]} invalid onChange={vi.fn()} />,
    );
    expect(screen.getByText(/strictement croissants, de 1 à 90/)).toHaveClass("text-destructive");
    for (const input of screen.getAllByRole("spinbutton")) {
      expect(input).toHaveAttribute("aria-invalid", "true");
    }
    rerender(<DelaysField value={["7", "14", "21"]} invalid={false} refused onChange={vi.fn()} />);
    expect(screen.getByText("Le serveur a refusé cette valeur : vérifie-la.")).toBeInTheDocument();
  });
});
