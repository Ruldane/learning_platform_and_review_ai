import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { MasterProfileView, ProfileSaveErrorView } from "../viewTypes";
import { DroppedBanner } from "./DroppedBanner";
import { displayedErrors, FieldErrorsContext } from "./fieldErrors";
import { cleanProfile } from "./profileDraft";
import { ProfileSections } from "./ProfileSections";

interface MasterProfileFormProps {
  profile: MasterProfileView;
  /** Texts of the lines that the check removed from the draft. */
  dropped: string[];
  saving: boolean;
  error: ProfileSaveErrorView | null;
  onSave: (profile: MasterProfileView) => void;
}

/**
 * The master profile to review and correct: nine collapsible sections, adding and removing rows,
 * sources shown as badges. « Enregistrer » returns the full profile; server errors (422) are
 * placed under their field by path. A new `profile` replaces the draft.
 */
export function MasterProfileForm({
  profile,
  dropped,
  saving,
  error,
  onSave,
}: MasterProfileFormProps) {
  const [draft, setDraft] = useState(profile);
  // The draft as it was sent: the indices of a 422 are read against it.
  const [sent, setSent] = useState(profile);
  const [source, setSource] = useState(profile);
  if (source !== profile) {
    setSource(profile);
    setDraft(profile);
    setSent(profile);
  }

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (saving) return;
    setSent(draft);
    onSave(cleanProfile(draft));
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label={t("cv.profile.label")}
      aria-busy={saving}
      className="flex flex-col gap-3"
    >
      <DroppedBanner dropped={dropped} />
      <p className="text-sm text-muted-foreground">{t("cv.profile.sourcesHint")}</p>
      <FieldErrorsContext value={displayedErrors(sent, error?.fields ?? {})}>
        <fieldset disabled={saving} className="flex flex-col gap-3">
          <ProfileSections
            profile={draft}
            onChange={(changes) => setDraft((current) => ({ ...current, ...changes }))}
          />
        </fieldset>
      </FieldErrorsContext>
      {error ? <InlineError message={error.message} /> : null}
      <Button type="submit" className="self-start" disabled={saving}>
        {saving ? t("cv.profile.saving") : t("cv.profile.save")}
      </Button>
    </form>
  );
}
