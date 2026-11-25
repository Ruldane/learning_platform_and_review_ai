import { readTiers } from "../tierChoices";
import type { ModelChoice, PresetMap, PresetName, SettingsOut, Tier, TierChoices } from "../types";
import { buildUserSettings } from "../userSettings";
import type { TrackAction } from "./useActionError";
import { useUpdateSettings } from "./useUpdateSettings";

const ignore = () => undefined;

/** Level actions: apply a preset, or change the model of a single level. */
export function useTierActions(settings: SettingsOut | undefined, track: TrackAction) {
  const update = useUpdateSettings();

  const save = (tiers: TierChoices) => {
    if (!settings) return;
    track(() => update.mutateAsync(buildUserSettings(settings, tiers))).catch(ignore);
  };

  return {
    pending: update.isPending,
    applyPreset: (presets: PresetMap, name: PresetName) => save(presets[name]),
    changeTier: (tier: Tier, choice: ModelChoice) =>
      save({ ...readTiers(settings?.tiers), [tier]: choice }),
  };
}
