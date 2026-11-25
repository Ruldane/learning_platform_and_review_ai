import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";

/** No cards left to review: the next step is to go to the quizzes. */
export function ReviewDone() {
  const navigate = useNavigate();
  return (
    <EmptyState
      title={t("quiz.reviews.doneTitle")}
      description={t("quiz.reviews.doneDescription")}
      action={{ label: t("quiz.reviews.toQuiz"), onClick: () => void navigate("/study/quiz") }}
    />
  );
}
