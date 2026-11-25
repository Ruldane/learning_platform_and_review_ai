import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ModeSwitch } from "../../components/ModeSwitch";
import type { PreferencesView } from "../../components/viewTypes";
import { useSavePreferences } from "../../hooks/usePreferences";
import type { Preferences } from "../../types";

interface TeacherSettingsProps {
  /** The preferences read from the server; `undefined` until they arrive. */
  prefs: Preferences | undefined;
}

/** Only the settings the learner just touched, in the contract's terms. */
function changes(before: PreferencesView, next: PreferencesView): Partial<Preferences> {
  const patch: Partial<Preferences> = {};
  if (next.auto !== before.auto) patch.teacher_mode = next.auto ? "auto" : "on_demand";
  if (next.idle !== before.idle) patch.idle_trigger = next.idle;
  if (next.style !== before.style) patch.teacher_style = next.style;
  if (next.claudeWrites !== before.claudeWrites) patch.mcp_can_write_files = next.claudeWrites;
  return patch;
}

/**
 * The teacher settings and Claude's switch: each change sends only the setting
 * touched; the others (caps, switch set in another tab) are the server's.
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
