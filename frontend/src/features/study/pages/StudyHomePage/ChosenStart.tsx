import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ModePicker } from "../../components/ModePicker";
import { ChosenLessonCard } from "./ChosenLessonCard";
import type { ChosenLesson } from "./chosenLesson";
import type { StartProps } from "./startTypes";

/**
 * La leçon choisie (`?lecon=` ou « Demander au tuteur ») : mode, leçon, départ. Si une session est
 * déjà ouverte, elle reste à reprendre : le back n'en ouvre pas une seconde.
 */
export function ChosenStart({
  chosen,
  mode,
  onMode,
  starter,
  openSessionId,
}: StartProps & { chosen: ChosenLesson }) {
  const navigate = useNavigate();
  const start = () =>
    void starter.start({
      lesson_id: chosen.lessonId,
      mode,
      ...(chosen.question ? { question: chosen.question } : {}),
    });
  return (
    <>
      <ModePicker value={mode} onChange={onMode} />
      <ChosenLessonCard chosen={chosen} disabled={starter.pending} onStart={start} />
      {openSessionId ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">{t("study.home.chosen.open")}</p>
          <Button
            variant="outline"
            className="self-start"
            onClick={() => void navigate(`/etudier/session/${openSessionId}`)}
          >
            {t("study.block.resume")}
          </Button>
        </div>
      ) : null}
    </>
  );
}
