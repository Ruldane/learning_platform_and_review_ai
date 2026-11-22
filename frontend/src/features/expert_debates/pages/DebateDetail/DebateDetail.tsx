import { t } from "@/shared/i18n/t";
import type { Debate } from "../../api";
import { DebateJudgment } from "../../components/DebateJudgment";
import { ExpertStatement } from "../../components/ExpertStatement";

interface Props {
  debate: Debate;
  saving: boolean;
  onSave: (text: string) => void;
}

function progress(status: Debate["status"]) {
  switch (status) {
    case "failed":
      return t("expertDebates.failed");
    case "cancelled":
      return t("expertDebates.cancelled");
    case "paused":
    case "waiting_user":
      return t("expertDebates.paused");
    default:
      return t("expertDebates.waiting");
  }
}

export function DebateDetail({ debate, saving, onSave }: Props) {
  return (
    <div className="flex min-w-0 flex-col gap-4">
      <h2 className="text-xl font-semibold break-words">{debate.question}</h2>
      {debate.status !== "completed" && <p role="status">{progress(debate.status)}</p>}
      {debate.speeches.map((speech) => (
        <ExpertStatement key={speech.role} {...speech} />
      ))}
      {debate.status === "completed" && debate.speeches.length > 0 && (
        <DebateJudgment
          key={debate.id}
          judgment={debate.judgment}
          saving={saving}
          onSave={onSave}
        />
      )}
    </div>
  );
}
