import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PresetMap, ProviderOption, TierChoices } from "../viewTypes";
import { TiersSection } from "./TiersSection";

const haiku = { provider: "anthropic", model: "claude-haiku-5-5" };
const tiers: TierChoices = { rapide: haiku, standard: haiku, fort: haiku, vision: haiku };
const glm = { provider: "glm", model: "glm-5.3" };
const presets: PresetMap = {
  all_haiku: tiers,
  haiku_sonnet_strong: tiers,
  all_glm: { rapide: glm, standard: glm, fort: glm, vision: glm },
  all_openai: tiers,
};
const providers: ProviderOption[] = [
  { name: "anthropic", label: "Anthropic", has_key: true, models: ["claude-haiku-5-5"] },
];

function renderSection(visionEnabled = true) {
  const onApplyPreset = vi.fn();
  render(
    <TiersSection
      tiers={tiers}
      presets={presets}
      providers={providers}
      visionEnabled={visionEnabled}
      disabled={false}
      onApplyPreset={onApplyPreset}
      onChangeTier={vi.fn()}
    />,
  );
  return onApplyPreset;
}

describe("TiersSection", () => {
  it("affiche le titre, les préréglages et les quatre niveaux", () => {
    renderSection();
    expect(
      screen.getByRole("heading", { level: 2, name: "Modèle par niveau" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tout Haiku" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getAllByRole("row")).toHaveLength(5);
  });

  it("remonte le préréglage choisi", async () => {
    const user = userEvent.setup();
    const onApplyPreset = renderSection();
    await user.click(screen.getByRole("button", { name: "Tout GLM" }));
    expect(onApplyPreset).toHaveBeenCalledWith("all_glm");
  });

  it("avertit seulement quand la vision est désactivée", () => {
    renderSection(false);
    expect(screen.getByRole("note")).toBeInTheDocument();
  });

  it("n'avertit pas quand la vision est disponible", () => {
    renderSection(true);
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });
});
