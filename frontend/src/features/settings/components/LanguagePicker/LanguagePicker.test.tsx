import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LanguagePicker } from "./LanguagePicker";

describe("LanguagePicker", () => {
  it("propose les six langues, cochées selon la valeur", () => {
    render(<LanguagePicker value={["fr", "en"]} onChange={vi.fn()} />);
    expect(screen.getAllByRole("checkbox")).toHaveLength(6);
    expect(screen.getByLabelText("Français")).toBeChecked();
    expect(screen.getByLabelText("Anglais")).toBeChecked();
    expect(screen.getByLabelText("Espagnol")).not.toBeChecked();
    expect(screen.getByRole("group", { name: "Langues de recherche" })).toBeInTheDocument();
  });

  it("ajoute une langue en gardant l'ordre canonique", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LanguagePicker value={["en", "fr"]} onChange={onChange} />);
    await user.click(screen.getByLabelText("Allemand"));
    expect(onChange).toHaveBeenCalledWith(["fr", "en", "de"]);
  });

  it("décoche une langue quand il en reste une autre", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LanguagePicker value={["fr", "en"]} onChange={onChange} />);
    await user.click(screen.getByLabelText("Anglais"));
    expect(onChange).toHaveBeenCalledWith(["fr"]);
  });

  it("garde au moins une langue : la dernière ne se décoche pas", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LanguagePicker value={["fr"]} onChange={onChange} />);
    const last = screen.getByLabelText("Français");
    expect(last).toBeDisabled();
    await user.click(last);
    expect(onChange).not.toHaveBeenCalled();
  });
});
