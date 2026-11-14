import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { MasterProfileForm } from "../../components/MasterProfileForm";
import { useSaveProfile } from "../../hooks/useSaveProfile";
import { toProfileView } from "../../profileView";
import { cvKeys } from "../../queryKeys";
import type { ProfileOut } from "../../types";
import { ReimportSection } from "./ReimportSection";
import { SavedNotice } from "./SavedNotice";
import { VersionsSection } from "./VersionsSection";

interface ProfileEditorProps {
  current: ProfileOut;
  isDraft: boolean;
}

/**
 * Le profil à relire (brouillon) ou à corriger (validé). « Valider mon profil » envoie `PUT` avec la
 * version relue ; un 409 dit que le profil a changé et propose de le recharger (la saisie n'est
 * perdue que si on recharge).
 */
export function ProfileEditor({ current, isDraft }: ProfileEditorProps) {
  const client = useQueryClient();
  const [savedVersion, setSavedVersion] = useState<number | null>(null);
  // Une référence stable : le formulaire se réinitialise quand elle change.
  const view = useMemo(() => toProfileView(current.data), [current]);
  const { save, saving, error, conflict, clear } = useSaveProfile(current.version, setSavedVersion);
  const reload = () => {
    clear();
    void client.invalidateQueries({ queryKey: cvKeys.profile });
  };
  const title = isDraft
    ? t("cv.profilePage.draftTitle")
    : t("cv.profilePage.validatedTitle", { version: current.version });
  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">{title}</h2>
        {isDraft ? (
          <p className="max-w-prose text-muted-foreground">{t("cv.profilePage.draftHint")}</p>
        ) : null}
        <SavedNotice version={savedVersion} />
        <MasterProfileForm
          profile={view}
          dropped={current.dropped}
          saving={saving}
          error={error}
          onSave={(profile) => {
            setSavedVersion(null);
            save(profile);
          }}
        />
        {conflict ? (
          <Button variant="outline" className="self-start" onClick={reload}>
            {t("cv.profilePage.reload")}
          </Button>
        ) : null}
      </section>
      <ReimportSection />
      <VersionsSection />
    </div>
  );
}
