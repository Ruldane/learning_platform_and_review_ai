import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { InlineError } from "@/shared/ui/states/InlineError";
import { DocumentUpload } from "../../components/DocumentUpload";
import { useDocumentActions } from "../../hooks/useDocumentActions";
import { useDocuments } from "../../hooks/useDocuments";
import { DocumentsSection } from "./DocumentsSection";
import { LearnedProgress } from "./LearnedProgress";

/** Documents : import (fichier, lien, texte collé), liste avec statuts, et « Déjà appris ». */
export function DocumentsPage({ createSocket }: { createSocket?: SocketFactory }) {
  const documents = useDocuments();
  const actions = useDocumentActions();
  const { upload, learn } = actions;
  const nameOf = (id: string) => documents.data?.find((d) => d.id === id)?.name ?? "";

  return (
    <div className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">{t("memory.page.documentsTitle")}</h1>
        <p className="mt-2 text-muted-foreground">{t("memory.page.documentsIntro")}</p>
      </header>
      <DocumentUpload
        resetKey={actions.sent}
        busy={upload.isPending}
        error={upload.isError ? errorMessage(upload.error) : null}
        onUploadFile={(file) => upload.mutate({ kind: "file", file })}
        onSubmitUrl={(url) => upload.mutate({ kind: "url", url })}
        onSubmitText={(title, text) => upload.mutate({ kind: "text", title, text })}
      />
      {actions.duplicate ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("memory.upload.duplicate")}
        </p>
      ) : null}
      {learn.isError ? <InlineError message={errorMessage(learn.error)} /> : null}
      {actions.learnings.map((learning) => (
        <LearnedProgress
          key={learning.sessionId}
          sessionId={learning.sessionId}
          documentName={nameOf(learning.documentId)}
          onFinished={() => actions.finishLearning(learning.documentId)}
          createSocket={createSocket}
        />
      ))}
      <DocumentsSection
        documents={documents}
        learningIds={actions.learningIds}
        onMarkLearned={(id) => learn.mutate(id)}
      />
    </div>
  );
}
