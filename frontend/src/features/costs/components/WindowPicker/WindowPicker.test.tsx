import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WindowPicker } from "./WindowPicker";

describe("WindowPicker", () => {
  it("offers 7, 30 and 90 days and says which one is chosen", () => {
    render(<WindowPicker value={30} onChange={() => undefined} />);
    const group = screen.getByRole("group", { name: "Period" });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "7 days" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: "30 days" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "90 days" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("reports the chosen window", async () => {
    const onChange = vi.fn();
    render(<WindowPicker value={30} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "90 days" }));
    expect(onChange).toHaveBeenCalledWith(90);
  });
});
