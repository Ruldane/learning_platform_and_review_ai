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
  /** Textes des lignes que la vérification a retirées du brouillon. */
  dropped: string[];
  saving: boolean;
  error: ProfileSaveErrorView | null;
  onSave: (profile: MasterProfileView) => void;
}

/**
 * Le profil maître à relire et corriger : neuf sections repliables, ajout et retrait de lignes,
 * sources visibles en badges. « Enregistrer » renvoie le profil complet ; les erreurs du serveur
 * (422) se placent sous leur champ par leur chemin. Un nouveau `profile` remplace le brouillon.
 */
export function MasterProfileForm({
  profile,
  dropped,
  saving,
  error,
  onSave,
}: MasterProfileFormProps) {
  const [draft, setDraft] = useState(profile);
  // Le brouillon tel qu'il est parti : c'est sur lui que se lisent les indices d'un 422.
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
