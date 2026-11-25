import { useState } from "react";
import type { FormEvent } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useSaveStudySettings } from "../../hooks/useSaveStudySettings";
import {
  hasStudyErrors,
  sameStudyDraft,
  studyDraftErrors,
  toStudyDraft,
  type StudyDraft,
} from "../../studySettings";
import type { SettingsOut } from "../../types";
import { ReviewFields } from "./ReviewFields";
import { RhythmFields } from "./RhythmFields";
import { Section } from "../../components/Section";

/**
 * The study form. The draft exists only while editing (`null`: the server's
 * settings are shown). Saving is by button, never on each keystroke; a field out of the
 * contract bounds blocks sending. On failure the draft stays.
 */
export function StudySettingsEditor({ settings }: { settings: SettingsOut }) {
  const stored = toStudyDraft(settings);
  const [draft, setDraft] = useState<StudyDraft | null>(null);
  const saver = useSaveStudySettings(settings);
  const value = draft ?? stored;
  const errors = studyDraftErrors(value);
  const dirty = draft !== null && !sameStudyDraft(draft, stored);
  const blocked = !dirty || hasStudyErrors(errors) || saver.pending;

  const edit = (next: StudyDraft) => {
    saver.reset();
    setDraft(next);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (blocked || draft === null) return;
    saver.save(draft).then(
      () => setDraft(null),
      () => undefined, // the error is shown from the mutation; the input is kept
    );
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">{t("settings.study.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("settings.study.intro")}</p>
      </header>
      <Section title={t("settings.study.sections.rhythm")}>
        <RhythmFields draft={value} errors={errors} onChange={edit} />
      </Section>
      <Section title={t("settings.study.sections.review")}>
        <ReviewFields draft={value} errors={errors} onChange={edit} />
      </Section>
      {saver.error ? <InlineError message={errorMessage(saver.error)} /> : null}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={blocked}>
          {saver.pending ? t("settings.study.saving") : t("settings.study.save")}
        </Button>
        <p role="status" className="text-sm text-muted-foreground">
          {saver.saved && !dirty ? t("settings.study.saved") : null}
          {dirty && !saver.pending ? t("settings.study.unsaved") : null}
        </p>
      </div>
    </form>
  );
}
