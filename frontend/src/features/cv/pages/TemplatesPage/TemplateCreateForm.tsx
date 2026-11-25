import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { NameField } from "./NameField";
import { PdfFields } from "./PdfFields";
import { ProfileCvAction } from "./ProfileCvAction";
import { useTemplateForm } from "./useTemplateForm";

/**
 * Create a template: a name, then an uploaded or already imported PDF. A refusal is in French;
 * when the vision model is missing (409), a link leads to the settings.
 */
export function TemplateCreateForm({
  onCreated,
  profileDocumentId = null,
}: {
  onCreated: (templateId: string) => void;
  /** The profile's last CV import, if any: the « Utiliser le CV de mon profil » action. */
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
