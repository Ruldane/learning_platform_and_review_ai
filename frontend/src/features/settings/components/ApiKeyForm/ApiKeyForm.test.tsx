import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiKeyForm } from "./ApiKeyForm";

describe("ApiKeyForm", () => {
  it("a un champ mot de passe étiqueté par le fournisseur", () => {
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={vi.fn()} />);
    const input = screen.getByLabelText("Clé API Anthropic");
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autocomplete", "new-password");
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

  it("n'écrit jamais la clé dans le DOM (attribut value), pendant la saisie ni après un échec", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockRejectedValue(new Error("refus"));
    const { container } = render(
      <ApiKeyForm providerLabel="Anthropic" pending={false} onSave={onSave} />,
    );
    const input = screen.getByLabelText(/clé/i);
    await user.type(input, "sk-ant-secret-1234");
    expect(input.getAttribute("value") ?? "").not.toContain("sk-ant-secret");
    expect(container.innerHTML).not.toContain("sk-ant-secret");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));
    expect(onSave).toHaveBeenCalledWith("sk-ant-secret-1234");
    // Après l'échec, la saisie est gardée pour réessayer, mais seulement dans la valeur du champ.
    expect(input).toHaveValue("sk-ant-secret-1234");
    expect(input.getAttribute("value") ?? "").not.toContain("sk-ant-secret");
    expect(container.innerHTML).not.toContain("sk-ant-secret");
  });

  it("réactive puis désactive Enregistrer selon la présence de texte", async () => {
    const user = userEvent.setup();
    render(<ApiKeyForm providerLabel="Anthropic" pending={false} onSave={vi.fn()} />);
    const button = screen.getByRole("button", { name: "Enregistrer" });
    await user.type(screen.getByLabelText(/clé/i), "a");
    expect(button).toBeEnabled();
    await user.clear(screen.getByLabelText(/clé/i));
    expect(button).toBeDisabled();
  });
});
