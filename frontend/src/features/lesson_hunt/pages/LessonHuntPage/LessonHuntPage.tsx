import { useParams } from "react-router";
import { t } from "@/shared/i18n/t";
import { ActiveHunt } from "./ActiveHunt";
import { StartHunt } from "./StartHunt";
export function LessonHuntPage() {
  const { lessonId, huntId } = useParams();
  return (
    <div className="flex max-w-3xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("lessonHunt.title")}</h1>
      {huntId ? <ActiveHunt key={huntId} huntId={huntId} /> : null}
      {lessonId ? <StartHunt key={lessonId} lessonId={lessonId} /> : null}
    </div>
  );
}
