import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { TeachOut } from "../../types";
import { TeacherActivity } from "./TeacherActivity";

interface TeachFeedbackProps {
  ideSessionId: string;
  /** La dernière réponse de `POST /teach`, s'il y en a eu une. */
  result: TeachOut | undefined;
  error: unknown;
  createSocket?: SocketFactory;
}

/**
 * Ce que le dernier appel au professeur a donné : un graphe qui travaille, un renvoi à la note
 * précédente (même erreur au même endroit), ou la raison pour laquelle rien n'est parti.
 */
export function TeachFeedback({ ideSessionId, result, error, createSocket }: TeachFeedbackProps) {
  if (error) return <InlineError message={errorMessage(error)} />;
  if (!result) return null;
  if (result.skipped)
    return (
      <p role="status" className="text-sm">
        {t(`ide.teacher.skipped.${result.skipped}`)}
      </p>
    );
  if (result.reference_note_id) {
    return (
      <p role="status" className="text-sm">
        {t("ide.teacher.reference")}
      </p>
    );
  }
  if (!result.session_id) return null;
  return (
    <TeacherActivity
      key={result.session_id}
      ideSessionId={ideSessionId}
      teacherSessionId={result.session_id}
      createSocket={createSocket}
    />
  );
}
