import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { NameField } from "./NameField";
import { PdfFields } from "./PdfFields";
import { ProfileCvAction } from "./ProfileCvAction";
import { useTemplateForm } from "./useTemplateForm";

/**
 * Créer un modèle : un nom, puis un PDF envoyé ou un PDF déjà importé. Un refus se dit en français ;
 * quand le modèle de vision manque (409), un lien mène aux réglages.
 */
export function TemplateCreateForm({
  onCreated,
  profileDocumentId = null,
}: {
  onCreated: (templateId: string) => void;
  /** Le CV du dernier import du profil, s'il est encore là : l'action « Utiliser le CV de mon profil ». */
  profileDocumentId?: string | null;
}) {
  const form = useTemplateForm(onCreated);
  return (
    <form
      onSubmit={form.submit}
      aria-label={t("cv.templatesPage.formTitle")}
      aria-busy={form.pending}
      className="flex max-w-xl flex-col gap-4"
    >
      <NameField value={form.name} disabled={form.pending} onChange={form.setName} />
      <PdfFields
        disabled={form.pending}
        fileChosen={form.file !== null}
        imported={form.imported}
        documentId={form.documentId}
        onFile={form.pick}
        onDocument={form.setDocumentId}
      />
      {form.problem ? <InlineError message={form.problem} /> : null}
      {form.visionUnavailable ? (
        <Link to="/settings/models" className="text-sm font-medium underline underline-offset-4">
          {t("cv.templatesPage.settingsLink")}
        </Link>
      ) : null}
      {form.launchMenu}
      {profileDocumentId ? (
        <ProfileCvAction
          disabled={form.pending}
          onUse={() => form.createFromProfile(profileDocumentId)}
        />
      ) : null}
      <Button
        type="submit"
        className="self-start"
        disabled={form.pending || form.name.trim() === ""}
      >
        {form.pending ? t("cv.templatesPage.pending") : t("cv.templatesPage.submit")}
      </Button>
    </form>
  );
}
