import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { KindPicker } from "./KindPicker";

describe("KindPicker", () => {
  it("offers the six kinds, in order", () => {
    render(<KindPicker value={[]} onChange={vi.fn()} />);
    const names = screen.getAllByRole("checkbox").map((box) => box.parentElement?.textContent);
    expect(names).toEqual([
      "Document", "Acquired skill", "Lesson", "Source", "Posting", "Decision",
    ]);
  });

  it("adds and removes a kind", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<KindPicker value={["skill"]} onChange={onChange} />);
    await user.click(screen.getByRole("checkbox", { name: "Posting" }));
    expect(onChange).toHaveBeenLastCalledWith(["skill", "posting"]);
    rerender(<KindPicker value={["skill"]} onChange={onChange} />);
    await user.click(screen.getByRole("checkbox", { name: "Acquired skill" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});
