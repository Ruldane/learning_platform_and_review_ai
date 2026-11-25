import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { GoalForm } from "./GoalForm";

const TEXT = "What you want to learn or achieve";
const ROLE = "Target role (optional)";
const DEADLINE = "Deadline (optional)";
const HOURS = "Hours available per week (optional)";
const SUBMIT = "Convene the Council";

function setup(busy = false) {
  const onSubmit = vi.fn();
  render(<GoalForm busy={busy} onSubmit={onSubmit} />);
  return { onSubmit, user: userEvent.setup() };
}

describe("GoalForm", () => {
  it("sends the goal with its optional fields", async () => {
    const { onSubmit, user } = setup();
    await user.type(screen.getByLabelText(TEXT), "  Devenir ingénieure data  ");
    await user.type(screen.getByLabelText(ROLE), "Data engineer");
    await user.type(screen.getByLabelText(DEADLINE), "2099-06-30");
    await user.type(screen.getByLabelText(HOURS), "8");
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledWith({
      text: "Devenir ingénieure data",
      targetRole: "Data engineer",
      deadline: "2099-06-30",
      weeklyHours: 8,
    });
  });

  it("sends nulls for the empty optional fields", async () => {
    const { onSubmit, user } = setup();
    await user.type(screen.getByLabelText(TEXT), "Apprendre Rust");
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).toHaveBeenCalledWith({
      text: "Apprendre Rust",
      targetRole: null,
      deadline: null,
      weeklyHours: null,
    });
  });

  it.each([
    ["", "Describe your goal in at least 5 characters."],
    ["abc", "Describe your goal in at least 5 characters."],
    ["x".repeat(501), "500 characters max."],
  ])("refuses the text %j", async (typed, message) => {
    const { onSubmit, user } = setup();
    if (typed) {
      await user.click(screen.getByLabelText(TEXT));
      await user.paste(typed);
    }
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(screen.getByLabelText(TEXT)).toBeInvalid();
  });

  it("refuses a past deadline and today", async () => {
    const { onSubmit, user } = setup();
    await user.type(screen.getByLabelText(TEXT), "Apprendre Rust");
    await user.type(screen.getByLabelText(DEADLINE), "2020-01-01");
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("The deadline must be a future date.");
  });

  it.each(["0", "41", "2.5", "-3"])("refuses %s hours per week", async (hours) => {
    const { onSubmit, user } = setup();
    await user.type(screen.getByLabelText(TEXT), "Apprendre Rust");
    await user.type(screen.getByLabelText(HOURS), hours);
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Between 1 and 40 hours per week");
  });

  it("refuses a target role over 120 characters", async () => {
    const { onSubmit, user } = setup();
    await user.type(screen.getByLabelText(TEXT), "Apprendre Rust");
    await user.click(screen.getByLabelText(ROLE));
    await user.paste("r".repeat(121));
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("120 characters max.");
  });

  it("locks the form while the goal is being sent", () => {
    setup(true);
    expect(screen.getByLabelText(TEXT)).toBeDisabled();
    expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
  });
});
