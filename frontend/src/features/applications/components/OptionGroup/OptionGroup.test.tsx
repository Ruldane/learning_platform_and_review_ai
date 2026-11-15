import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OptionGroup } from "./OptionGroup";

const OPTIONS = [
  { value: "a", label: "Option A", hint: "Première." },
  { value: "b", label: "Option B" },
];

describe("OptionGroup", () => {
  it("is a named group of radio buttons with the chosen one checked and the hint read", () => {
    render(
      <OptionGroup legend="Formule" name="mode" options={OPTIONS} value="a" onChange={vi.fn()} />,
    );
    const group = screen.getByRole("group", { name: "Formule" });
    expect(group).toBeVisible();
    expect(screen.getByRole("radio", { name: "Option A" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Option A" })).toHaveAccessibleDescription(
      "Première.",
    );
    expect(screen.getByRole("radio", { name: "Option B" })).not.toBeChecked();
  });

  it("changes the choice by click and by the arrow keys", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <OptionGroup legend="Formule" name="mode" options={OPTIONS} value="a" onChange={onChange} />,
    );
    await user.click(screen.getByRole("radio", { name: "Option B" }));
    expect(onChange).toHaveBeenCalledWith("b");
    onChange.mockClear();
    screen.getByRole("radio", { name: "Option A" }).focus();
    await user.keyboard("{ArrowDown}");
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("locks every choice when disabled", () => {
    render(
      <OptionGroup
        legend="Formule"
        name="mode"
        options={OPTIONS}
        value="a"
        disabled
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("radio", { name: "Option B" })).toBeDisabled();
  });
});
