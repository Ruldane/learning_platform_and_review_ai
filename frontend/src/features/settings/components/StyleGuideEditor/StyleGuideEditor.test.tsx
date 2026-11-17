import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StyleGuideEditor } from "./StyleGuideEditor";

describe("StyleGuideEditor", () => {
  it("shows the text with a character counter, and reports what is typed", async () => {
    const onChange = vi.fn();
    render(<StyleGuideEditor value="Court." onChange={onChange} />);
    const field = screen.getByLabelText("Guide de style personnel");
    expect(field).toHaveValue("Court.");
    expect(screen.getByText("6 caractères")).toBeInTheDocument();
    await userEvent.setup().type(field, "!");
    expect(onChange).toHaveBeenCalledWith("Court.!");
  });

  it("counts characters, not UTF-16 units", () => {
    render(<StyleGuideEditor value="é😀" onChange={vi.fn()} />);
    expect(screen.getByText("2 caractères")).toBeInTheDocument();
  });

  it("flags the field when the server refused it", () => {
    render(<StyleGuideEditor value="x" refused onChange={vi.fn()} />);
    expect(screen.getByLabelText("Guide de style personnel")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByText("Le serveur a refusé cette valeur : vérifie-la.")).toBeInTheDocument();
  });
});
