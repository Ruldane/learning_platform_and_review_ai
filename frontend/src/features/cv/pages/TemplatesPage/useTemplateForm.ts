import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { MAX_PDF_BYTES } from "../../components/viewTypes";
import { useCreateTemplate } from "../../hooks/useCreateTemplate";
import { useDocuments } from "../../hooks/useVersions";

/** Un PDF choisi qui n'en est pas un, ou trop lourd : le texte du refus, sinon `null`. */
function fileProblem(file: File): string | null {
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    return t("cv.import.notPdf");
  }
  return file.size > MAX_PDF_BYTES ? t("cv.import.tooBig") : null;
}

/**
 * L'état du formulaire de création d'un modèle : nom, PDF envoyé ou PDF déjà importé. Le PDF
 * envoyé l'emporte ; sans aucun des deux, le formulaire dit ce qui manque.
 */
export function useTemplateForm(onCreated: (templateId: string) => void) {
  const { create, pending, error, visionUnavailable } = useCreateTemplate(onCreated);
  const documents = useDocuments();
  const [name, setName] = useState(t("cv.templatesPage.nameDefault"));
  const [file, setFile] = useState<File | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [local, setLocal] = useState<string | null>(null);
  const imported = (documents.data ?? []).filter(
    (doc) => doc.source_kind === "pdf" && doc.status === "indexed",
  );

  const pick = (picked: File | null) => {
    setFile(picked);
    setLocal(picked ? fileProblem(picked) : null);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    const trimmed = name.trim();
    if (file && local === null) create({ name: trimmed, file });
    else if (!file && documentId !== "") create({ name: trimmed, documentId });
    else if (!file) setLocal(t("cv.templatesPage.needFile"));
  };
  return {
    name,
    setName,
    file,
    pick,
    documentId,
    setDocumentId,
    imported,
    pending,
    problem: local ?? error,
    visionUnavailable,
    submit,
  };
}
