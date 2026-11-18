import { useId, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

export interface PostingChoice {
  id: string;
  label: string;
}

interface PostingPickerProps {
  /** Les offres analysées, les plus récentes d'abord. */
  postings: PostingChoice[];
  onPick: (postingId: string) => void;
}

/** Choisir une offre analysée pour lancer la revue du CV et générer un CV aligné sur elle. */
export function PostingPicker({ postings, onPick }: PostingPickerProps) {
  const id = useId();
  const [chosen, setChosen] = useState(postings[0]?.id ?? "");
  if (postings.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("cv.postingPicker.none")}</p>;
  }
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (chosen) onPick(chosen);
  };
  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <div className="flex min-w-64 flex-1 flex-col gap-1">
        <label htmlFor={id} className="text-sm font-medium">
          {t("cv.postingPicker.label")}
        </label>
        <select
          id={id}
          value={chosen}
          onChange={(event) => setChosen(event.target.value)}
          className={fieldClass}
        >
          {postings.map((posting) => (
            <option key={posting.id} value={posting.id}>
              {posting.label}
            </option>
          ))}
        </select>
      </div>
      <Button type="submit" disabled={!chosen}>
        {t("cv.postingPicker.submit")}
      </Button>
    </form>
  );
}
