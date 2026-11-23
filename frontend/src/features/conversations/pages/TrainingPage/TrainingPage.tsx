import { useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { t } from "@/shared/i18n/t";
import { ConversationList } from "../../components/ConversationList";
import { useConversationList } from "../../hooks/useConversationList";
import { newTrainingPath, trainingPath } from "../../hooks/useTraining";
import { trainingSkillId } from "../../hooks/useTrainingTopic";
import { TrainingPanel } from "./TrainingPanel";

export function TrainingPage() {
  const { studyId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [revision, clear] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const skillId = trainingSkillId(params.get("competence"));
  const fresh = !studyId && params.has("nouvelle");
  const start = () => {
    void navigate(newTrainingPath(skillId));
    heading.current?.focus();
  };
  const select = (id: string) => {
    void navigate(trainingPath(id));
    heading.current?.focus();
  };
  const { sidebar } = useConversationList("training", (action) => {
    if (action.kind === "clear") {
      clear((current) => current + 1);
      heading.current?.focus();
    }
    if (action.kind === "delete" || action.kind === "wipe") start();
  });
  return (
    <div className="flex flex-col gap-4">
      <h1 tabIndex={-1} ref={heading} className="text-2xl font-semibold">
        {t("training.title")}
      </h1>
      <div className="grid items-start gap-4 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <ConversationList
          {...sidebar}
          selected={studyId ?? null}
          onCreate={start}
          onSelect={select}
        />
        <TrainingPanel
          key={`${studyId ?? (fresh ? "new" : "open")}:${revision}`}
          studyId={studyId}
          skillId={skillId}
          fresh={fresh}
        />
      </div>
    </div>
  );
}
