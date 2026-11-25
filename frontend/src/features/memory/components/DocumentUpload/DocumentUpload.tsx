import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { FileTab } from "./FileTab";
import { TextTab } from "./TextTab";
import { UploadTabs, type UploadTab } from "./UploadTabs";
import { UrlTab } from "./UrlTab";

interface DocumentUploadProps {
  /** True while sending: the fields and buttons are disabled. */
  busy: boolean;
  /** Error from the previous send, rendered by the parent (server message). */
  error: string | null;
  onUploadFile: (file: File) => void;
  onSubmitUrl: (url: string) => void;
  onSubmitText: (title: string, text: string) => void;
  /**
   * Changes after a successful send: the link and pasted text forms are remounted, so
   * emptied (a failure keeps the input). The current tab does not change.
   */
  resetKey?: number;
}

/** Importing a document: file (20 MB, PDF, DOCX, Markdown, text), link or pasted text. */
export function DocumentUpload(props: DocumentUploadProps) {
  const { busy, error, onUploadFile, onSubmitUrl, onSubmitText, resetKey = 0 } = props;
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
        {/* `key`: switching tab starts again with a new form (size message included). */}
        {tab === "file" ? <FileTab key="file" busy={busy} onUploadFile={onUploadFile} /> : null}
        {tab === "url" ? (
          <UrlTab key={`url-${resetKey}`} busy={busy} onSubmitUrl={onSubmitUrl} />
        ) : null}
        {tab === "text" ? (
          <TextTab key={`text-${resetKey}`} busy={busy} onSubmitText={onSubmitText} />
        ) : null}
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
