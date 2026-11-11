import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { KindPicker } from "./KindPicker";

describe("KindPicker", () => {
  it("offers the six kinds, in order", () => {
    render(<KindPicker value={[]} onChange={vi.fn()} />);
    const names = screen.getAllByRole("checkbox").map((box) => box.parentElement?.textContent);
    expect(names).toEqual(["Document", "Acquis", "Leçon", "Source", "Offre", "Décision"]);
  });

  it("adds and removes a kind", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(<KindPicker value={["acquis"]} onChange={onChange} />);
    await user.click(screen.getByRole("checkbox", { name: "Offre" }));
    expect(onChange).toHaveBeenLastCalledWith(["acquis", "offre"]);
    rerender(<KindPicker value={["acquis"]} onChange={onChange} />);
    await user.click(screen.getByRole("checkbox", { name: "Acquis" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});
