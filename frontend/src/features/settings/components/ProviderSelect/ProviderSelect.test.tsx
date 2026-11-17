import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProviderOption } from "../viewTypes";
import { ProviderSelect } from "./ProviderSelect";

const options: ProviderOption[] = [
  { name: "anthropic", label: "Anthropic", has_key: true, models: null },
  { name: "openai", label: "OpenAI", has_key: false, models: null },
];

describe("ProviderSelect", () => {
  it("marque les fournisseurs sans clé sans les désactiver", () => {
    render(
      <ProviderSelect label="Fournisseur" value="anthropic" options={options} onPick={vi.fn()} />,
    );
    expect(screen.getByRole("combobox", { name: "Fournisseur" })).toHaveValue("anthropic");
    expect(screen.getByRole("option", { name: "OpenAI (aucune clé)" })).toBeEnabled();
  });

  it("remonte le fournisseur choisi", async () => {
    const user = userEvent.setup();
    const onPick = vi.fn();
    render(
      <ProviderSelect label="Fournisseur" value="anthropic" options={options} onPick={onPick} />,
    );
    await user.selectOptions(screen.getByRole("combobox"), "openai");
    expect(onPick).toHaveBeenCalledWith("openai");
  });

  it("garde visible un fournisseur courant absent de la liste", () => {
    render(
      <ProviderSelect label="Fournisseur" value="ancien" options={options} onPick={vi.fn()} />,
    );
    expect(screen.getByRole("combobox")).toHaveValue("ancien");
  });

  it("se désactive", () => {
    render(
      <ProviderSelect
        label="Fournisseur"
        value="anthropic"
        options={options}
        disabled
        onPick={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("propose un premier choix « aucun » quand on lui donne son texte", async () => {
    const onPick = vi.fn();
    render(
      <ProviderSelect
        label="Fournisseur"
        value=""
        options={options}
        emptyLabel="Niveau par défaut"
        onPick={onPick}
      />,
    );
    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("");
    expect(screen.getAllByRole("option")[0]).toHaveTextContent("Niveau par défaut");
    // aucune option parasite
    expect(screen.getAllByRole("option")).toHaveLength(options.length + 1);
    await userEvent.setup().selectOptions(select, options[0]!.name);
    expect(onPick).toHaveBeenCalledWith(options[0]!.name);
  });
});
