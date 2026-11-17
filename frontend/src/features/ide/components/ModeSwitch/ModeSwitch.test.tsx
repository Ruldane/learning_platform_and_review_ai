import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ModeSwitch } from "./ModeSwitch";

describe("ModeSwitch", () => {
  it("switches automatic help and the 30 s option separately", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ModeSwitch preferences={{ auto: true, idle: false, style: "guide" }} pending={false} onChange={onChange} />,
    );
    const auto = screen.getByRole("switch", {
      name: "Le professeur intervient tout seul après une erreur",
    });
    expect(auto).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /30 s sans bouger de ligne/ })).not.toBeChecked();
    await user.click(auto);
    expect(onChange).toHaveBeenLastCalledWith({ auto: false, idle: false, style: "guide" });
    await user.click(screen.getByRole("checkbox", { name: /30 s sans bouger de ligne/ }));
    expect(onChange).toHaveBeenLastCalledWith({ auto: true, idle: true, style: "guide" });
  });

  it("writes the mode in words and waits for the server without losing the focus", async () => {
    const onChange = vi.fn();
    render(<ModeSwitch
        preferences={{ auto: false, idle: true, style: "pair" }}
        pending
        onChange={onChange}
      />);
    expect(screen.getByText("Sur demande")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("switch"));
    await user.click(screen.getByRole("checkbox"));
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("switch")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("checkbox")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("checkbox")).toBeEnabled();
  });

  it("offers guide and pair as two exclusive choices, each described", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ModeSwitch
        preferences={{ auto: true, idle: false, style: "guide" }}
        pending={false}
        onChange={onChange}
      />,
    );
    expect(screen.getByRole("radio", { name: /Guide/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Binôme/ })).not.toBeChecked();
    await user.click(screen.getByRole("radio", { name: /Binôme/ }));
    expect(onChange).toHaveBeenLastCalledWith({ auto: true, idle: false, style: "pair" });
  });

  it("does not change the style while a write is pending", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ModeSwitch
        preferences={{ auto: true, idle: false, style: "guide" }}
        pending
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole("radio", { name: /Binôme/ }));
    expect(onChange).not.toHaveBeenCalled();
  });
});
