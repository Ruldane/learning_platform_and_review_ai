import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

/** « Utiliser le CV de mon profil » : crée le modèle depuis le CV du dernier import du profil. */
export function ProfileCvAction({ disabled, onUse }: { disabled: boolean; onUse: () => void }) {
  return (
    <div className="flex flex-col gap-1">
      <Button
        type="button"
        variant="outline"
        className="self-start"
        disabled={disabled}
        onClick={onUse}
      >
        {t("cv.templatesPage.profileCv")}
      </Button>
      <span className="text-xs text-muted-foreground">{t("cv.templatesPage.profileCvHint")}</span>
    </div>
  );
}
