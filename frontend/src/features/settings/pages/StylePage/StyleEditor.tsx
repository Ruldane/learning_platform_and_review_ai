import { useState } from "react";
import type { FormEvent } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { SaveBar } from "../../components/SaveBar";
import { StyleGuideEditor } from "../../components/StyleGuideEditor";
import { useSaveSettings } from "../../hooks/useSaveSettings";
import { isRefused, refusedFields } from "../../refusedFields";
import type { SettingsOut } from "../../types";
import { withStyleGuide } from "../../userSettings";

/**
 * The style form: the draft exists only while editing (`null`: the text of the
 * server). Saving by button; on failure, the text stays.
 */
export function StyleEditor({ settings }: { settings: SettingsOut }) {
  const [draft, setDraft] = useState<string | null>(null);
  const saver = useSaveSettings();
  const value = draft ?? settings.style_guide;
  const dirty = draft !== null && draft !== settings.style_guide;
  const blocked = !dirty || saver.pending;

  const edit = (text: string) => {
    saver.reset();
    setDraft(text);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (blocked || draft === null) return;
    // A keystroke made during the send stays: the draft is sent to the server only if it has not
    // changed.
    saver.save(withStyleGuide(settings, draft)).then(
      () => setDraft((current) => (current === draft ? null : current)),
      () => undefined, // the error is shown from the mutation; the text is kept
    );
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("settings.style.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("settings.style.intro")}</p>
      </header>
      <StyleGuideEditor
        value={value}
        refused={isRefused(refusedFields(saver.error), "style_guide")}
        onChange={edit}
      />
      {saver.error ? <InlineError message={errorMessage(saver.error)} /> : null}
      <SaveBar
        pending={saver.pending}
        saved={saver.saved}
        dirty={dirty}
        blocked={blocked}
        labels={{
          save: t("settings.style.save"),
          saving: t("settings.style.saving"),
          saved: t("settings.style.saved"),
          unsaved: t("settings.style.unsaved"),
        }}
      />
    </form>
  );
}
