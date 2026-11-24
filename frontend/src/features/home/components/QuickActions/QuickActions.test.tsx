import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QuickActions } from "./QuickActions";

function setup() {
  const handlers = {
    onStart: vi.fn(),
    onReview: vi.fn(),
    onAddPosting: vi.fn(),
    onCapture: vi.fn(),
  };
  render(<QuickActions {...handlers} />);
  return handlers;
}

describe("QuickActions", () => {
  it("has the four buttons in the order of the spec", () => {
    setup();
    const group = screen.getByRole("group", { name: "Quick actions" });
    const names = Array.from(group.querySelectorAll("button")).map((b) => b.textContent);
    expect(names).toEqual(["Start my block", "Review", "Add a posting", "Capture"]);
  });

  it("is operable from the keyboard alone, in tab order", async () => {
    const user = userEvent.setup();
    const handlers = setup();
    await user.tab();
    expect(screen.getByRole("button", { name: "Start my block" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await user.tab();
    await user.keyboard(" ");
    await user.tab();
    await user.keyboard("{Enter}");
    await user.tab();
    await user.keyboard("{Enter}");
    expect(handlers.onStart).toHaveBeenCalledOnce();
    expect(handlers.onReview).toHaveBeenCalledOnce();
    expect(handlers.onAddPosting).toHaveBeenCalledOnce();
    expect(handlers.onCapture).toHaveBeenCalledOnce();
  });
});
