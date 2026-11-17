import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ModeSwitch } from "../../components/ModeSwitch";
import type { PreferencesView } from "../../components/viewTypes";
import { useSavePreferences } from "../../hooks/usePreferences";
import type { Preferences } from "../../types";

interface TeacherSettingsProps {
  /** Les préférences lues sur le serveur ; `undefined` tant qu'elles ne sont pas arrivées. */
  prefs: Preferences | undefined;
}

/** Les seuls réglages que la personne vient de toucher, dans les mots du contrat. */
function changes(before: PreferencesView, next: PreferencesView): Partial<Preferences> {
  const patch: Partial<Preferences> = {};
  if (next.auto !== before.auto) patch.teacher_mode = next.auto ? "auto" : "on_demand";
  if (next.idle !== before.idle) patch.idle_trigger = next.idle;
  if (next.style !== before.style) patch.teacher_style = next.style;
  if (next.claudeWrites !== before.claudeWrites) patch.mcp_can_write_files = next.claudeWrites;
  return patch;
}

/**
 * Les réglages du professeur et l'interrupteur de Claude : chaque changement n'envoie que le réglage
 * touché ; les autres (plafonds, interrupteur réglé dans un autre onglet) sont ceux du serveur.
 */
export function TeacherSettings({ prefs }: TeacherSettingsProps) {
  const save = useSavePreferences();
  const view: PreferencesView | null = prefs
    ? {
        auto: prefs.teacher_mode === "auto",
        idle: prefs.idle_trigger,
        style: prefs.teacher_style,
        claudeWrites: prefs.mcp_can_write_files,
      }
    : null;
  return (
    <>
      {view ? (
        <ModeSwitch
          preferences={view}
          pending={save.isPending}
          onChange={(next) => save.mutate(changes(view, next))}
        />
      ) : (
        <p className="text-sm">{t("ide.mode.loading")}</p>
      )}
      {save.isError ? <InlineError message={t("ide.mode.saveFailed")} /> : null}
    </>
  );
}
