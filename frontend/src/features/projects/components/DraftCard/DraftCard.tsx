import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { DraftView } from "../viewTypes";
import { DraftActions, type CopyState } from "./DraftActions";
import { DraftField } from "./DraftField";
import { DraftNotice } from "./DraftNotice";
import { useDraftText } from "./useDraftText";

interface DraftCardProps {
  draft: DraftView;
  /** Enregistre le texte retouché. */
  onSave: (content: string) => void;
  /** Copie le texte affiché ; une promesse rejetée signale l'échec. L'application ne publie rien. */
  onCopy: (content: string) => void | Promise<void>;
  /** L'enregistrement est en cours. */
  saving?: boolean;
  /** Le refus ou la panne du dernier enregistrement de CE brouillon, dit sur sa carte. */
  error?: string | null;
}

/** Un brouillon au nom de January : texte modifiable, « Enregistrer », « Copier » et l'avertissement « À vérifier ». */
export function DraftCard({ draft, onSave, onCopy, saving = false, error = null }: DraftCardProps) {
  const id = useId();
  const { value, setValue, message, tryOk } = useDraftText(draft.content, error);
  const [copy, setCopy] = useState<CopyState>("idle");

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
      <DraftField
        id={id}
        value={value}
        message={message}
        onChange={(next) => {
          setValue(next);
          setCopy("idle");
        }}
      />
      <DraftActions
        canSave={value !== draft.content}
        saving={saving}
        copy={copy}
        onSave={() => {
          if (tryOk()) onSave(value);
        }}
        onCopy={() => void copyText()}
      />
      <p className="text-xs text-muted-foreground">{t("projects.draft.notSent")}</p>
    </article>
  );
}
