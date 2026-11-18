import { useId, useState, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { QuickActions } from "./QuickActions";

interface ChatComposerProps {
  /** Le professeur répond (ou une demande part) : « Envoyer » attend, les raccourcis ignorent les clics. */
  busy: boolean;
  /** Une exécution a échoué : « Pourquoi cette erreur ? » a quelque chose à expliquer. */
  canExplain: boolean;
  /** Rend `true` quand la question est partie : la saisie n'est vidée que dans ce cas. */
  onSend: (question: string) => Promise<boolean>;
  onHint: () => void;
  onWhy: () => void;
}

/**
 * La saisie du chat : Entrée envoie, Maj+Entrée fait un retour à la ligne. Une question refusée ou
 * en erreur reste dans la zone de texte. Les raccourcis (Indice, Pourquoi cette erreur ?) restent
 * près de la saisie ; occupés, ils restent focalisables (`aria-disabled`).
 */
export function ChatComposer({ busy, canExplain, onSend, onHint, onWhy }: ChatComposerProps) {
  const fieldId = useId();
  const [text, setText] = useState("");
  const question = text.trim();
  const submit = async () => {
    if (question === "" || busy) return;
    if (await onSend(question)) setText("");
  };
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    void submit();
  };
  return (
    <form
      className="flex flex-col gap-2 border-t border-border p-3"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <QuickActions busy={busy} canExplain={canExplain} onHint={onHint} onWhy={onWhy} />
      <label htmlFor={fieldId} className="sr-only">
        {t("ide.teacher.question")}
      </label>
      <textarea
        id={fieldId}
        rows={2}
        value={text}
        maxLength={2000}
        placeholder={t("ide.chat.placeholder")}
        aria-describedby={`${fieldId}-help`}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        className={cn(fieldClass, "h-auto resize-none py-1.5")}
      />
      <div className="flex items-center justify-between gap-2">
        <p id={`${fieldId}-help`} className="text-xs text-muted-foreground">
          {t("ide.chat.shortcuts")}
        </p>
        <Button type="submit" size="sm" disabled={question === "" || busy}>
          {t("ide.chat.send")}
        </Button>
      </div>
    </form>
  );
}
