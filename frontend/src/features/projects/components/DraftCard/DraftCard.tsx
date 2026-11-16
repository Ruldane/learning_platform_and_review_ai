import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { DraftView } from "../viewTypes";
import { DraftActions, type CopyState } from "./DraftActions";
import { DraftNotice } from "./DraftNotice";

interface DraftCardProps {
  draft: DraftView;
  /** Enregistre le texte retouché. */
  onSave: (content: string) => void;
  /** Copie le texte affiché ; une promesse rejetée signale l'échec. L'application ne publie rien. */
  onCopy: (content: string) => void | Promise<void>;
  /** L'enregistrement est en cours. */
  saving?: boolean;
}

/** Un brouillon au nom de January : texte modifiable, « Enregistrer », « Copier » et l'avertissement « À vérifier ». */
export function DraftCard({ draft, onSave, onCopy, saving = false }: DraftCardProps) {
  const id = useId();
  const [value, setValue] = useState(draft.content);
  const [seen, setSeen] = useState(draft.content);
  const [copy, setCopy] = useState<CopyState>("idle");
  if (seen !== draft.content) {
    setSeen(draft.content);
    setValue(draft.content);
  }

  const copyText = async () => {
    try {
      await onCopy(value);
      setCopy("copied");
    } catch {
      setCopy("failed");
    }
  };

  return (
    <article className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-sm">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <label htmlFor={id} className="font-medium">
          {t(`projects.draft.kind.${draft.kind}`)}
        </label>
        {draft.edited ? (
          <span className="text-xs text-muted-foreground">{t("projects.draft.edited")}</span>
        ) : null}
      </header>
      <DraftNotice draft={draft} />
      <textarea
        id={id}
        rows={6}
        value={value}
        onChange={(event) => {
          setValue(event.target.value);
          setCopy("idle");
        }}
        className={`${fieldClass} h-auto py-2`}
      />
      <DraftActions
        canSave={value !== draft.content}
        saving={saving}
        copy={copy}
        onSave={() => onSave(value)}
        onCopy={() => void copyText()}
      />
      <p className="text-xs text-muted-foreground">{t("projects.draft.notSent")}</p>
    </article>
  );
}
