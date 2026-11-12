import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { LibraryFilterValue } from "../viewTypes";
import { LibraryFilters } from "./LibraryFilters";

const NONE: LibraryFilterValue = { programId: null, type: null, lang: null, status: null };
const PROGRAMS = [
  { id: "p1", title: "Python pour la data" },
  { id: "p2", title: "SQL" },
];

function setup(value: LibraryFilterValue = NONE) {
  const onChange = vi.fn();
  render(<LibraryFilters value={value} programs={PROGRAMS} onChange={onChange} />);
  return { onChange, user: userEvent.setup() };
}

describe("LibraryFilters", () => {
  it("filters by program, type, language and status", async () => {
    const { onChange, user } = setup();
    await user.selectOptions(screen.getByLabelText("Programme"), "p2");
    expect(onChange).toHaveBeenLastCalledWith({ ...NONE, programId: "p2" });
    await user.selectOptions(screen.getByLabelText("Type"), "video");
    expect(onChange).toHaveBeenLastCalledWith({ ...NONE, type: "video" });
    await user.selectOptions(screen.getByLabelText("Langue"), "fr");
    expect(onChange).toHaveBeenLastCalledWith({ ...NONE, lang: "fr" });
    await user.selectOptions(screen.getByLabelText("Statut"), "to_read");
    expect(onChange).toHaveBeenLastCalledWith({ ...NONE, status: "to_read" });
  });

  it("keeps the other filters when one changes, and clears one with « Tous »", async () => {
    const { onChange, user } = setup({ ...NONE, type: "video", status: "read" });
    expect(screen.getByLabelText("Type")).toHaveValue("video");
    await user.selectOptions(screen.getByLabelText("Langue"), "en");
    expect(onChange).toHaveBeenLastCalledWith({
      ...NONE,
      type: "video",
      status: "read",
      lang: "en",
    });
    await user.selectOptions(screen.getByLabelText("Type"), "");
    expect(onChange).toHaveBeenLastCalledWith({ ...NONE, status: "read" });
  });
});
