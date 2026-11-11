import { describe, expect, it } from "vitest";
import { modelsFixture, settingsFixture } from "./fixtures";
import { readPresets, readTiers } from "./tierChoices";

describe("readTiers", () => {
  it("renvoie les quatre niveaux", () => {
    expect(readTiers(settingsFixture.tiers)).toEqual(settingsFixture.tiers);
  });

  it("complète un niveau absent par un choix vide plutôt que de planter", () => {
    const tiers = readTiers({ rapide: { provider: "glm", model: "x" } });
    expect(tiers.fort).toEqual({ provider: "", model: "" });
    expect(tiers.rapide).toEqual({ provider: "glm", model: "x" });
  });
});

describe("readPresets", () => {
  it("renvoie les quatre préréglages, chacun avec ses quatre niveaux", () => {
    const presets = readPresets(modelsFixture.presets);
    expect(Object.keys(presets)).toEqual([
      "all_haiku",
      "haiku_sonnet_strong",
      "all_glm",
      "all_openai",
    ]);
    expect(presets.haiku_sonnet_strong.fort.model).toBe("claude-sonnet-5-5");
  });
});
