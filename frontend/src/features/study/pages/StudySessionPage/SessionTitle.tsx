import { t } from "@/shared/i18n/t";
import type { StudySessionOut } from "../../types";

/** The lesson studied, its module and the tutor's mode. */
export function SessionTitle({ session }: { session: StudySessionOut }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold">{session.lesson_title}</h1>
      <p className="text-sm text-muted-foreground">
        {t("study.session.context", { module: session.module_title, lesson: session.lesson_title })}
        {" · "}
        {t("study.session.mode", { mode: t(`study.modes.${session.mode}.label`) })}
      </p>
    </div>
  );
}
