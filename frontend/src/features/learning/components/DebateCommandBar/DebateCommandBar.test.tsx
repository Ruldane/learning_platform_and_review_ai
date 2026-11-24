import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DebateCommandBar } from "./DebateCommandBar";

describe("DebateCommandBar", () => {
  it("offers the four commands in a named group", () => {
    render(<DebateCommandBar disabled={false} onCommand={vi.fn()} />);
    const group = screen.getByRole("group", { name: "Debate commands" });
    expect(group.querySelectorAll("button")).toHaveLength(4);
    for (const name of [
      "Relancer un tour",
      "Move on to proposals",
      "More concrete",
      "Shorter",
    ]) {
      expect(screen.getByRole("button", { name })).toBeEnabled();
    }
  });

  it("sends to_proposals", async () => {
    const user = userEvent.setup();
    const onCommand = vi.fn();
    render(<DebateCommandBar disabled={false} onCommand={onCommand} />);
    await user.click(screen.getByRole("button", { name: "Move on to proposals" }));
    expect(onCommand).toHaveBeenCalledWith("to_proposals");
  });

  it.each([
    ["Relancer un tour", "another_round"],
    ["More concrete", "more_concrete"],
    ["Shorter", "shorter"],
  ])("%s sends %s", async (name, command) => {
    const user = userEvent.setup();
    const onCommand = vi.fn();
    render(<DebateCommandBar disabled={false} onCommand={onCommand} />);
    await user.click(screen.getByRole("button", { name }));
    expect(onCommand).toHaveBeenCalledWith(command);
  });

  it("disables every command", async () => {
    const user = userEvent.setup();
    const onCommand = vi.fn();
    render(<DebateCommandBar disabled onCommand={onCommand} />);
    for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Shorter" }));
    expect(onCommand).not.toHaveBeenCalled();
  });
});
