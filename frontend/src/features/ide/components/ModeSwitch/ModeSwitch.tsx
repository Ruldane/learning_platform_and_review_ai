import { t } from "@/shared/i18n/t";
import type { PreferencesView } from "../viewTypes";
import { IdleOption } from "./IdleOption";
import { StylePicker } from "./StylePicker";
import { SwitchRow } from "./SwitchRow";

interface ModeSwitchProps {
  preferences: PreferencesView;
  /** Une écriture est en cours : les réglages ne bougent plus avant la réponse. */
  pending: boolean;
  onChange: (next: PreferencesView) => void;
}

/**
 * Les réglages du professeur : intervenir tout seul après une erreur (sinon, seulement sur
 * demande), en option coupée par défaut proposer de l'aide après 30 s sans bouger de ligne, sa
 * façon d'aider (guide : par indices ; binôme : réfléchit avec toi), et l'interrupteur qui laisse
 * Claude (par le MCP) écrire dans les fichiers : éteint par défaut, réglé ici et nulle part
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
