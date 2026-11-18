import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProgramPicker } from "./ProgramPicker";

const programs = [
  { id: "p2", title: "Bases du ML" },
  { id: "p1", title: "Python pour la data" },
];

describe("ProgramPicker", () => {
  it("shows the chosen program and reports another choice", async () => {
    const onChange = vi.fn();
    render(<ProgramPicker programs={programs} value="p2" onChange={onChange} />);
    const select = screen.getByRole("combobox", { name: "Programme" });
    expect(select).toHaveValue("p2");
    await userEvent.selectOptions(select, "Python pour la data");
    expect(onChange).toHaveBeenCalledWith("p1");
  });
});
