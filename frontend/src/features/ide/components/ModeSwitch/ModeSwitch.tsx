import { t } from "@/shared/i18n/t";
import type { PreferencesView } from "../viewTypes";
import { IdleOption } from "./IdleOption";
import { StylePicker } from "./StylePicker";
import { SwitchRow } from "./SwitchRow";

interface ModeSwitchProps {
  preferences: PreferencesView;
  /** A save is in progress: the settings stay put until the response. */
  pending: boolean;
  onChange: (next: PreferencesView) => void;
}

/**
 * Teacher settings: step in on its own after an error (otherwise, only on
 * request), an option off by default to offer help after 30 s without moving, its
 * help style (guide: by hints; pair: thinks with you), and the switch that lets
 * Claude (via the MCP) write to the files: off by default, set here and nowhere
 * ailleurs.
 */
export function ModeSwitch({ preferences, pending, onChange }: ModeSwitchProps) {
  const { auto, idle, style, claudeWrites } = preferences;
  return (
    <fieldset className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3">
      <legend className="px-1 text-sm font-medium">{t("ide.mode.title")}</legend>
      <SwitchRow
        label={t("ide.mode.auto")}
        stateText={auto ? t("ide.mode.autoOn") : t("ide.mode.autoOff")}
        checked={auto}
        pending={pending}
        onToggle={() => onChange({ ...preferences, auto: !auto })}
      />
      <IdleOption
        checked={idle}
        pending={pending}
        onToggle={(next) => onChange({ ...preferences, idle: next })}
      />
      <StylePicker
        value={style}
        pending={pending}
        onPick={(next) => onChange({ ...preferences, style: next })}
      />
      <SwitchRow
        label={t("ide.mode.claudeWrites")}
        stateText={`${t("ide.mode.claudeWrites")} : ${
          claudeWrites ? t("ide.mode.claudeWritesOn") : t("ide.mode.claudeWritesOff")
        }`}
        checked={claudeWrites}
        pending={pending}
        hint={t("ide.mode.claudeWritesHint")}
        onToggle={() => onChange({ ...preferences, claudeWrites: !claudeWrites })}
      />
    </fieldset>
  );
}
