import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ModeSwitch } from "../../components/ModeSwitch";
import { useSavePreferences } from "../../hooks/usePreferences";
import type { Preferences } from "../../types";

interface TeacherSettingsProps {
  /** Les préférences lues sur le serveur ; `undefined` tant qu'elles ne sont pas arrivées. */
  prefs: Preferences | undefined;
}

/** Les réglages du professeur : chaque changement réécrit toutes les préférences (plafonds gardés). */
export function TeacherSettings({ prefs }: TeacherSettingsProps) {
  const save = useSavePreferences();
  return (
    <>
      {prefs ? (
        <ModeSwitch
          preferences={{
            auto: prefs.teacher_mode === "auto",
            idle: prefs.idle_trigger,
            style: prefs.teacher_style,
            claudeWrites: prefs.mcp_can_write_files,
          }}
          pending={save.isPending}
          onChange={(next) =>
            save.mutate({
              ...prefs,
              teacher_mode: next.auto ? "auto" : "on_demand",
              idle_trigger: next.idle,
              teacher_style: next.style,
              mcp_can_write_files: next.claudeWrites,
            })
          }
        />
      ) : (
        <p className="text-sm">{t("ide.mode.loading")}</p>
      )}
      {save.isError ? <InlineError message={t("ide.mode.saveFailed")} /> : null}
    </>
  );
}
