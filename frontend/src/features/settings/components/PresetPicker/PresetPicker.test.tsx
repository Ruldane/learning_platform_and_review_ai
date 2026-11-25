import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PresetMap, TierChoices } from "../viewTypes";
import { matchPreset } from "./matchPreset";
import { PresetPicker } from "./PresetPicker";

function all(provider: string, model: string): TierChoices {
  const choice = { provider, model };
  return { fast: choice, standard: choice, strong: choice, vision: choice };
}

const presets: PresetMap = {
  all_haiku: all("anthropic", "claude-haiku-5-5"),
  haiku_sonnet_strong: {
    ...all("anthropic", "claude-haiku-5-5"),
    strong: { provider: "anthropic", model: "claude-sonnet-5-5" },
  },
  all_glm: all("glm", "glm-5.3"),
  all_openai: all("openai", "gpt-6-luna"),
};

describe("matchPreset", () => {
  it("reconnaît un préréglage au fournisseur et au modèle de chaque niveau", () => {
    expect(matchPreset(all("glm", "glm-5.3"), presets)).toBe("all_glm");
    expect(matchPreset(presets.haiku_sonnet_strong, presets)).toBe("haiku_sonnet_strong");
  });

  it("renvoie null quand un seul niveau diffère", () => {
    const current = { ...all("glm", "glm-5.3"), vision: { provider: "glm", model: "autre" } };
    expect(matchPreset(current, presets)).toBeNull();
  });
});

describe("PresetPicker", () => {
  it("applique un préréglage", async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    render(<PresetPicker presets={presets} current={presets.all_haiku} onApply={onApply} />);
    await user.click(screen.getByRole("button", { name: "All GLM" }));
    expect(onApply).toHaveBeenCalledWith("all_glm");
  });

  it("propose les quatre préréglages", () => {
    render(<PresetPicker presets={presets} current={presets.all_haiku} onApply={vi.fn()} />);
    for (const name of [
      "All Haiku",
      "Haiku with Sonnet for the strong tier",
      "All GLM",
      "All OpenAI",
    ]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
  });

  it("marque le préréglage en vigueur", () => {
    render(<PresetPicker presets={presets} current={presets.all_openai} onApply={vi.fn()} />);
    expect(screen.getByRole("button", { name: "All OpenAI" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "All GLM" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByText("Custom")).not.toHaveAttribute("aria-current");
  });

  it("affiche « Personnalisé » quand les niveaux ne correspondent à aucun préréglage", () => {
    const current = { ...presets.all_haiku, strong: { provider: "glm", model: "glm-5.3" } };
    render(<PresetPicker presets={presets} current={current} onApply={vi.fn()} />);
    expect(screen.getByText("Custom")).toHaveAttribute("aria-current", "true");
    for (const button of screen.getAllByRole("button")) {
      expect(button).toHaveAttribute("aria-pressed", "false");
    }
  });

  it("désactive les boutons pendant l'enregistrement", () => {
    render(
      <PresetPicker presets={presets} current={presets.all_haiku} disabled onApply={vi.fn()} />,
    );
    for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
  });
});
