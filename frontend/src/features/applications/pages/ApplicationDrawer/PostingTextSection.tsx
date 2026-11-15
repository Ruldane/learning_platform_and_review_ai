import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DraftField, type FieldSpec } from "../../components/DraftField";
import type { ApplicationDetail, ApplicationPatch } from "../../types";
import { DrawerSection } from "./DrawerSection";

const POSTING_TEXT_MAX = 60_000;
const FIELD: FieldSpec = {
  key: "postingText",
  label: t("applications.drawer.postingField"),
  kind: "textarea",
  maxLength: POSTING_TEXT_MAX,
};

interface PostingTextSectionProps {
  detail: ApplicationDetail;
  pending: boolean;
  onSave: (patch: ApplicationPatch) => Promise<boolean>;
}

/**
 * Le texte de l'offre d'une fiche saisie sans elle (à la main ou en une phrase) : sans lui, le kit
 * de candidature ne peut pas se préparer. Une fiche qui a déjà un texte, ou une offre liée, le dit.
 */
export function PostingTextSection({ detail, pending, onSave }: PostingTextSectionProps) {
  const [text, setText] = useState("");
  const kept = Boolean(detail.posting_text) || detail.posting_id !== null;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || text.trim() === "") return;
    void onSave({ posting_text: text.trim() });
  }

  return (
    <DrawerSection title={t("applications.drawer.postingTitle")}>
      {kept ? (
        <p className="text-sm text-muted-foreground">{t("applications.drawer.postingKept")}</p>
      ) : (
        <form noValidate onSubmit={submit} className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">{t("applications.drawer.postingMissing")}</p>
          <DraftField spec={FIELD} value={text} onChange={setText} />
          <div>
            <Button type="submit" disabled={pending || text.trim() === ""}>
              {t("applications.drawer.postingAction")}
            </Button>
          </div>
        </form>
      )}
    </DrawerSection>
  );
}
