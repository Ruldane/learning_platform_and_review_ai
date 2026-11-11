import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { FileTab } from "./FileTab";
import { TextTab } from "./TextTab";
import { UploadTabs, type UploadTab } from "./UploadTabs";
import { UrlTab } from "./UrlTab";

interface DocumentUploadProps {
  /** Vrai pendant l'envoi : les champs et les boutons sont désactivés. */
  busy: boolean;
  /** Erreur de l'envoi précédent, rendue par le parent (message du serveur). */
  error: string | null;
  onUploadFile: (file: File) => void;
  onSubmitUrl: (url: string) => void;
  onSubmitText: (title: string, text: string) => void;
}

/** Import d'un document : fichier (20 Mo, PDF, DOCX, Markdown, texte), lien ou texte collé. */
export function DocumentUpload(props: DocumentUploadProps) {
  const { busy, error, onUploadFile, onSubmitUrl, onSubmitText } = props;
  const [tab, setTab] = useState<UploadTab>("file");

  return (
    <div className="flex flex-col gap-3">
      <UploadTabs tab={tab} onChange={setTab} />
      <div
        role="tabpanel"
        id={`upload-panel-${tab}`}
        aria-labelledby={`upload-tab-${tab}`}
        className="flex flex-col gap-3"
      >
        {/* `key` : changer d'onglet repart d'un formulaire neuf (message de taille compris). */}
        {tab === "file" ? <FileTab key="file" busy={busy} onUploadFile={onUploadFile} /> : null}
        {tab === "url" ? <UrlTab key="url" busy={busy} onSubmitUrl={onSubmitUrl} /> : null}
        {tab === "text" ? <TextTab key="text" busy={busy} onSubmitText={onSubmitText} /> : null}
        {busy ? (
          <p role="status" className="text-sm text-muted-foreground">
            {t("memory.upload.busy")}
          </p>
        ) : null}
        {error ? <InlineError message={error} /> : null}
      </div>
    </div>
  );
}
