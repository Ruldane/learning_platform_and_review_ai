import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ModePicker } from "./ModePicker";

describe("ModePicker", () => {
  it("offers the three modes as radios in a named group", () => {
    render(<ModePicker value="socratic" onChange={vi.fn()} />);
    expect(screen.getByRole("radiogroup", { name: "Mode d'étude" })).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(3);
    expect(screen.getByRole("radio", { name: /Socratique/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Feynman/ })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: /Direct/ })).not.toBeChecked();
  });

  it("describes each mode", () => {
    render(<ModePicker value="direct" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: /Feynman/ })).toHaveAccessibleDescription(
      "Tu expliques chaque section avec tes mots, le tuteur repère les trous.",
    );
    expect(screen.getByRole("radio", { name: /Direct/ })).toBeChecked();
  });

  it("reports the chosen mode", async () => {
    const onChange = vi.fn();
    render(<ModePicker value="socratic" onChange={onChange} />);
    await userEvent.click(screen.getByRole("radio", { name: /Feynman/ }));
    expect(onChange).toHaveBeenCalledWith("feynman");
  });

  it("moves with the arrow keys", async () => {
    const onChange = vi.fn();
    render(<ModePicker value="socratic" onChange={onChange} />);
    screen.getByRole("radio", { name: /Socratique/ }).focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(onChange).toHaveBeenCalledWith("feynman");
  });
});
