import { useId } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { InlineError } from "@/shared/ui/states/InlineError";
import { PdfFields } from "./PdfFields";
import { useTemplateForm } from "./useTemplateForm";

/**
 * Créer un modèle : un nom, puis un PDF envoyé ou un PDF déjà importé. Un refus se dit en français ;
 * quand le modèle de vision manque (409), un lien mène aux réglages.
 */
export function TemplateCreateForm({ onCreated }: { onCreated: (templateId: string) => void }) {
  const nameId = useId();
  const form = useTemplateForm(onCreated);
  return (
    <form
      onSubmit={form.submit}
      aria-label={t("cv.templatesPage.formTitle")}
      aria-busy={form.pending}
      className="flex max-w-xl flex-col gap-4"
    >
      <div className="flex flex-col gap-1">
        <label htmlFor={nameId} className="text-sm font-medium">
          {t("cv.templatesPage.name")}
        </label>
        <input
          id={nameId}
          className={fieldClass}
          value={form.name}
          maxLength={120}
          required
          disabled={form.pending}
          onChange={(event) => form.setName(event.target.value)}
        />
      </div>
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
        <Link to="/reglages/modeles" className="text-sm font-medium underline underline-offset-4">
          {t("cv.templatesPage.settingsLink")}
        </Link>
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
