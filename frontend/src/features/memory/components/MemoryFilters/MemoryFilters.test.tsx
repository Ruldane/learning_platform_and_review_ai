import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NO_FILTERS } from "../viewFixtures";
import { MemoryFilters } from "./MemoryFilters";

describe("MemoryFilters", () => {
  it("changes the kind", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<MemoryFilters value={NO_FILTERS} authors={[]} onChange={onChange} />);
    await user.selectOptions(screen.getByLabelText("Type"), "Acquired skill");
    expect(onChange).toHaveBeenCalledWith({ ...NO_FILTERS, kind: "skill" });
  });

  it("changes the tag", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<MemoryFilters value={NO_FILTERS} authors={[]} onChange={onChange} />);
    await user.type(screen.getByLabelText("Tag"), "n");
    expect(onChange).toHaveBeenLastCalledWith({ ...NO_FILTERS, tag: "n" });
  });

  it("offers the authors with their display names", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <MemoryFilters value={NO_FILTERS} authors={["user", "archivist"]} onChange={onChange} />,
    );
    expect(screen.getByRole("option", { name: "You" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Author"), "Archivist");
    expect(onChange).toHaveBeenCalledWith({ ...NO_FILTERS, author: "archivist" });
  });

  it("changes the date bounds", () => {
    const onChange = vi.fn();
    render(<MemoryFilters value={NO_FILTERS} authors={[]} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-01-02" } });
    expect(onChange).toHaveBeenLastCalledWith({ ...NO_FILTERS, since: "2026-01-02" });
    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-02-03" } });
    expect(onChange).toHaveBeenLastCalledWith({ ...NO_FILTERS, until: "2026-02-03" });
  });

  it("shows the current value", () => {
    render(
      <MemoryFilters
        value={{ ...NO_FILTERS, kind: "lesson", tag: "nlp" }}
        authors={[]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Type")).toHaveValue("lesson");
    expect(screen.getByLabelText("Tag")).toHaveValue("nlp");
  });
});
