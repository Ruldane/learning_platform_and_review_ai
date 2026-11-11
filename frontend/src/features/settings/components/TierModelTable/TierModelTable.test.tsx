import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProviderOption, TierChoices } from "../viewTypes";
import { TierModelTable } from "./TierModelTable";

const providers: ProviderOption[] = [
  {
    name: "anthropic",
    label: "Anthropic",
    has_key: true,
    models: ["claude-haiku-5-5", "claude-sonnet-5-5"],
  },
];
const choice = { provider: "anthropic", model: "claude-haiku-5-5" };
const tiers: TierChoices = { rapide: choice, standard: choice, fort: choice, vision: choice };

describe("TierModelTable", () => {
  it("affiche les quatre niveaux avec leur usage", () => {
    render(<TierModelTable tiers={tiers} providers={providers} onChange={vi.fn()} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(4);
    expect(within(rows[0]!).getByText("Rapide")).toBeInTheDocument();
    expect(within(rows[0]!).getByText("Recherche, extraction, modération")).toBeInTheDocument();
    expect(screen.getByText("Débat, relecture, quiz, tutorat")).toBeInTheDocument();
    expect(screen.getByText("Planning, rédaction des leçons, entretiens")).toBeInTheDocument();
    expect(screen.getByText("Capture du design du CV")).toBeInTheDocument();
  });

  it("remonte le niveau modifié avec le nouveau choix", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<TierModelTable tiers={tiers} providers={providers} onChange={onChange} />);
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Modèle (Fort)" }),
      "claude-sonnet-5-5",
    );
    expect(onChange).toHaveBeenCalledWith("fort", {
      provider: "anthropic",
      model: "claude-sonnet-5-5",
    });
  });

  it("désactive les sélecteurs pendant l'enregistrement", () => {
    render(<TierModelTable tiers={tiers} providers={providers} disabled onChange={vi.fn()} />);
    for (const select of screen.getAllByRole("combobox")) expect(select).toBeDisabled();
  });
});
