import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

type Option = { id: string; title: string };

type Props = {
  programs: Option[];
  lessons: Option[];
  programId: string;
  lessonId: string;
  busy: boolean;
  onProgram: (id: string) => void;
  onLesson: (id: string) => void;
  onPrepare: () => void;
};

export function VariantPicker(props: Props) {
  const selectClass = "rounded border bg-background p-2";
  return (
    <form className="flex flex-wrap items-end gap-3" onSubmit={(event) => {
      event.preventDefault();
      props.onPrepare();
    }}>
      <label className="grid gap-1">
        {t("lessonVariants.program")}
        <select className={selectClass} value={props.programId}
          onChange={(event) => props.onProgram(event.target.value)}>
          <option value="">{t("lessonVariants.chooseProgram")}</option>
          {props.programs.map(({ id, title }) => <option key={id} value={id}>{title}</option>)}
        </select>
      </label>
      <label className="grid gap-1">
        {t("lessonVariants.lesson")}
        <select className={selectClass} value={props.lessonId}
          disabled={props.lessons.length === 0}
          onChange={(event) => props.onLesson(event.target.value)}>
          <option value="">{t("lessonVariants.chooseLesson")}</option>
          {props.lessons.map(({ id, title }) => <option key={id} value={id}>{title}</option>)}
        </select>
      </label>
      <Button type="submit" disabled={props.busy || !props.lessonId}>
        {t("lessonVariants.create")}
      </Button>
    </form>
  );
}
