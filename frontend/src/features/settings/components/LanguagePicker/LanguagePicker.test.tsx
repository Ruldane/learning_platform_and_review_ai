import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LanguagePicker } from "./LanguagePicker";

describe("LanguagePicker", () => {
  it("shows all six languages and checks the selected ones", () => {
    render(<LanguagePicker value={["fr", "en"]} onChange={vi.fn()} />);
    expect(screen.getAllByRole("checkbox")).toHaveLength(6);
    expect(screen.getByLabelText("French")).toBeChecked();
    expect(screen.getByLabelText("English")).toBeChecked();
    expect(screen.getByLabelText("Spanish")).not.toBeChecked();
    expect(screen.getByRole("group", { name: "Search languages" })).toBeInTheDocument();
  });

  it("adds a language in canonical order", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LanguagePicker value={["en", "fr"]} onChange={onChange} />);
    await user.click(screen.getByLabelText("German"));
    expect(onChange).toHaveBeenCalledWith(["fr", "en", "de"]);
  });

  it("unchecks a language when another one remains", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LanguagePicker value={["fr", "en"]} onChange={onChange} />);
    await user.click(screen.getByLabelText("English"));
    expect(onChange).toHaveBeenCalledWith(["fr"]);
  });

  it("prevents unchecking the last language", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LanguagePicker value={["fr"]} onChange={onChange} />);
    const last = screen.getByLabelText("French");
    expect(last).toBeDisabled();
    await user.click(last);
    expect(onChange).not.toHaveBeenCalled();
  });
});
