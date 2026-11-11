import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiKeyForm } from "./ApiKeyForm";

describe("ApiKeyForm", () => {
  it("a un champ mot de passe étiqueté par le fournisseur", () => {
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={vi.fn()} />);
    const input = screen.getByLabelText("Clé API Anthropic");
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autocomplete", "off");
    expect(input).toHaveValue("");
  });

  it("enregistre à Entrée, sans espaces autour, puis vide le champ", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={onSave} />);
    await user.type(screen.getByLabelText(/clé/i), "  sk-ant-1234  {Enter}");
    expect(onSave).toHaveBeenCalledWith("sk-ant-1234");
    expect(screen.getByLabelText(/clé/i)).toHaveValue("");
  });

  it("n'enregistre rien tant que le champ est vide", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={onSave} />);
    await user.type(screen.getByLabelText(/clé/i), "   {Enter}");
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled();
  });

  it("désactive l'enregistrement pendant une opération", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ApiKeyForm providerLabel="Anthropic" pending onSave={onSave} />);
    await user.type(screen.getByLabelText(/clé/i), "sk-ant-1234{Enter}");
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled();
  });
});
