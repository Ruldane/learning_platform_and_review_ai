import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProviderOption } from "../viewTypes";
import { TierModelSelect } from "./TierModelSelect";

const anthropic: ProviderOption = {
  name: "anthropic",
  label: "Anthropic",
  has_key: true,
  models: ["claude-haiku-5-5", "claude-sonnet-5-5"],
};
const glm: ProviderOption = { name: "glm", label: "GLM (Z.ai)", has_key: true, models: null };
const openai: ProviderOption = {
  name: "openai",
  label: "OpenAI",
  has_key: false,
  models: ["gpt-6-luna", "gpt-6.1-sol"],
};

describe("TierModelSelect", () => {
  it("passe en saisie libre sans liste de modèles", () => {
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "glm", model: "x" }}
        providers={[glm]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("textbox", { name: /modèle/i })).toHaveValue("x");
  });

  it("propose la liste des modèles du fournisseur quand elle existe", () => {
    render(
      <TierModelSelect
        tier="rapide"
        value={{ provider: "anthropic", model: "claude-haiku-5-5" }}
        providers={[anthropic, glm]}
        onChange={vi.fn()}
      />,
    );
    const select = screen.getByRole("combobox", { name: "Modèle (Rapide)" });
    expect(select).toHaveValue("claude-haiku-5-5");
    expect(screen.getByRole("option", { name: "claude-sonnet-5-5" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("garde visible un modèle courant absent de la liste", () => {
    render(
      <TierModelSelect
        tier="rapide"
        value={{ provider: "anthropic", model: "claude-ancien" }}
        providers={[anthropic]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox", { name: "Modèle (Rapide)" })).toHaveValue("claude-ancien");
  });

  it("marque un fournisseur sans clé mais le laisse sélectionnable", () => {
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-haiku-5-5" }}
        providers={[anthropic, openai]}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("option", { name: "OpenAI (aucune clé)" })).toBeEnabled();
    expect(screen.getByRole("option", { name: "Anthropic" })).toBeInTheDocument();
  });

  it("choisit le premier modèle du nouveau fournisseur", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-sonnet-5-5" }}
        providers={[anthropic, openai]}
        onChange={onChange}
      />,
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Fournisseur (Fort)" }),
      "openai",
    );
    expect(onChange).toHaveBeenCalledWith({ provider: "openai", model: "gpt-6-luna" });
  });

  it("change de modèle dans la liste", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-haiku-5-5" }}
        providers={[anthropic]}
        onChange={onChange}
      />,
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Modèle (Fort)" }),
      "claude-sonnet-5-5",
    );
    expect(onChange).toHaveBeenCalledWith({ provider: "anthropic", model: "claude-sonnet-5-5" });
  });

  it("vers un fournisseur à saisie libre : champ vide, rien n'est enregistré avant le modèle", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-sonnet-5-5" }}
        providers={[anthropic, glm]}
        onChange={onChange}
      />,
    );
    await user.selectOptions(screen.getByRole("combobox", { name: "Fournisseur (Fort)" }), "glm");
    const input = screen.getByRole("textbox", { name: /modèle/i });
    expect(input).toHaveValue("");
    expect(onChange).not.toHaveBeenCalled();
    await user.type(input, "glm-5.3");
    expect(onChange).not.toHaveBeenCalled();
    await user.tab();
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ provider: "glm", model: "glm-5.3" });
  });

  it("valide la saisie libre à Entrée, une seule fois par modification", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "glm", model: "x" }}
        providers={[glm]}
        onChange={onChange}
      />,
    );
    const input = screen.getByRole("textbox", { name: /modèle/i });
    await user.type(input, "y{Enter}");
    expect(onChange).toHaveBeenCalledWith({ provider: "glm", model: "xy" });
    await user.tab();
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("ne rappelle pas onChange quand la saisie libre n'a pas changé", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "glm", model: "x" }}
        providers={[glm]}
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole("textbox", { name: /modèle/i }));
    await user.tab();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("désactive les champs pendant l'enregistrement", () => {
    render(
      <TierModelSelect
        tier="fort"
        value={{ provider: "anthropic", model: "claude-haiku-5-5" }}
        providers={[anthropic]}
        disabled
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox", { name: "Fournisseur (Fort)" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "Modèle (Fort)" })).toBeDisabled();
  });
});
