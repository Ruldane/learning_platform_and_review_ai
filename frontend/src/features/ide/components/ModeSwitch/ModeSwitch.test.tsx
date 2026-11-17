import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ModeSwitch } from "./ModeSwitch";

describe("ModeSwitch", () => {
  it("switches automatic help and the 30 s option separately", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ModeSwitch
        preferences={{ auto: true, idle: false, style: "guide", claudeWrites: false }}
        pending={false}
        onChange={onChange}
      />,
    );
    const auto = screen.getByRole("switch", {
      name: "Le professeur intervient tout seul après une erreur",
    });
    expect(auto).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /30 s sans bouger de ligne/ })).not.toBeChecked();
    await user.click(auto);
    expect(onChange).toHaveBeenLastCalledWith({
      auto: false,
      idle: false,
      style: "guide",
      claudeWrites: false,
    });
    await user.click(screen.getByRole("checkbox", { name: /30 s sans bouger de ligne/ }));
    expect(onChange).toHaveBeenLastCalledWith({
      auto: true,
      idle: true,
      style: "guide",
      claudeWrites: false,
    });
  });

  it("writes the mode in words and waits for the server without losing the focus", async () => {
    const onChange = vi.fn();
    render(
      <ModeSwitch
        preferences={{ auto: false, idle: true, style: "pair", claudeWrites: false }}
        pending
        onChange={onChange}
      />,
    );
    expect(screen.getByText("Sur demande")).toBeInTheDocument();
    const user = userEvent.setup();
    for (const toggle of screen.getAllByRole("switch")) await user.click(toggle);
    await user.click(screen.getByRole("checkbox"));
    expect(onChange).not.toHaveBeenCalled();
    for (const toggle of screen.getAllByRole("switch")) {
      expect(toggle).toHaveAttribute("aria-disabled", "true");
    }
    expect(screen.getByRole("checkbox")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("checkbox")).toBeEnabled();
  });

  it("offers guide and pair as two exclusive choices, each described", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ModeSwitch
        preferences={{ auto: true, idle: false, style: "guide", claudeWrites: false }}
        pending={false}
        onChange={onChange}
      />,
    );
    expect(screen.getByRole("radio", { name: /Guide/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Binôme/ })).not.toBeChecked();
    await user.click(screen.getByRole("radio", { name: /Binôme/ }));
    expect(onChange).toHaveBeenLastCalledWith({
      auto: true,
      idle: false,
      style: "pair",
      claudeWrites: false,
    });
  });

  it("does not change the style while a write is pending", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ModeSwitch
        preferences={{ auto: true, idle: false, style: "guide", claudeWrites: false }}
        pending
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole("radio", { name: /Binôme/ }));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("offers Claude writing as its own switch, off by default, in words", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ModeSwitch
        preferences={{ auto: true, idle: false, style: "guide", claudeWrites: false }}
        pending={false}
        onChange={onChange}
      />,
    );
    const writes = screen.getByRole("switch", { name: "Claude peut écrire dans mes fichiers" });
    expect(writes).not.toBeChecked();
    expect(screen.getByText(/Non autorisé/)).toBeInTheDocument();
    await user.click(writes);
    expect(onChange).toHaveBeenLastCalledWith({
      auto: true,
      idle: false,
      style: "guide",
      claudeWrites: true,
    });
  });

  it("shows Claude writing as allowed when it is, and waits while a write is pending", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ModeSwitch
        preferences={{ auto: true, idle: false, style: "guide", claudeWrites: true }}
        pending
        onChange={onChange}
      />,
    );
    const writes = screen.getByRole("switch", { name: "Claude peut écrire dans mes fichiers" });
    expect(writes).toBeChecked();
    expect(screen.getByText(/Autorisé/)).toBeInTheDocument();
    await user.click(writes);
    expect(onChange).not.toHaveBeenCalled();
  });
});
