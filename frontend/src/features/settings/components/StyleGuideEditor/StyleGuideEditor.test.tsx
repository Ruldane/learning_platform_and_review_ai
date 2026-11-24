import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StyleGuideEditor } from "./StyleGuideEditor";

describe("StyleGuideEditor", () => {
  it("shows the text with a character counter, and reports what is typed", async () => {
    const onChange = vi.fn();
    render(<StyleGuideEditor value="Court." onChange={onChange} />);
    const field = screen.getByLabelText("Personal style guide");
    expect(field).toHaveValue("Court.");
    expect(screen.getByText("6 characters")).toBeInTheDocument();
    await userEvent.setup().type(field, "!");
    expect(onChange).toHaveBeenCalledWith("Court.!");
  });

  it("counts characters, not UTF-16 units", () => {
    render(<StyleGuideEditor value="é😀" onChange={vi.fn()} />);
    expect(screen.getByText("2 characters")).toBeInTheDocument();
  });

  it("flags the field when the server refused it", () => {
    render(<StyleGuideEditor value="x" refused onChange={vi.fn()} />);
    expect(screen.getByLabelText("Personal style guide")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(
      screen.getByText("Error: The server refused this value: check it."),
    ).toBeInTheDocument();
  });
});
