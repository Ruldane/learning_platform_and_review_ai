import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { formatDay } from "../format";
import type { ReminderView } from "../viewTypes";
import { ReminderActions } from "./ReminderActions";
import { ReminderContact } from "./ReminderContact";

interface ReminderCardProps {
  reminder: ReminderView;
  /** Copie le brouillon : l'application n'envoie rien. Une promesse rejetée signale l'échec. */
  onCopy: (draft: string) => void | Promise<void>;
  onDone: (id: string) => void;
  onPostpone: (id: string) => void;
  onIgnore: (id: string) => void;
}

type CopyState = "idle" | "copied" | "failed";

/**
 * Une relance à traiter : qui contacter, l'échéance, le brouillon et quatre boutons. Pour
 * `close_21` le bouton « Fait » devient « Classer en Sans réponse » (c'est la fiche qui change de
 * statut). La mention rappelle que rien n'est envoyé par l'application.
 */
export function ReminderCard({
  reminder,
  onCopy,
  onDone,
  onPostpone,
  onIgnore,
}: ReminderCardProps) {
  const [copy, setCopy] = useState<CopyState>("idle");
  const { id, draft } = reminder;

  async function copyDraft() {
    try {
      await onCopy(draft);
      setCopy("copied");
    } catch {
      setCopy("failed");
    }
  }

  return (
    <article className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-sm">
      <header className="flex flex-col gap-0.5">
        <h3 className="font-medium">{t(`applications.reminder.kind.${reminder.kind}`)}</h3>
        <p className="text-muted-foreground">
          {t("applications.reminder.for", { company: reminder.company, title: reminder.title })}
        </p>
        <p className="text-muted-foreground tabular-nums">
          {t("applications.reminder.dueOn", { date: formatDay(reminder.dueOn) })}
        </p>
      </header>
      <ReminderContact contact={reminder.contact} linkedinSearchUrl={reminder.linkedinSearchUrl} />
      <div role="group" aria-label={t("applications.reminder.draft")}>
        <pre className="max-h-64 overflow-auto rounded-lg border bg-background p-3 font-sans text-sm whitespace-pre-wrap">
          {draft}
        </pre>
      </div>
      <p role="status" className="min-h-5 text-xs text-muted-foreground">
        {copy === "copied" && t("applications.reminder.copied")}
        {copy === "failed" && t("applications.reminder.copyFailed")}
      </p>
      <ReminderActions
        closing={reminder.kind === "close_21"}
        onCopy={() => void copyDraft()}
        onDone={() => onDone(id)}
        onPostpone={() => onPostpone(id)}
        onIgnore={() => onIgnore(id)}
      />
      <p className="text-xs text-muted-foreground">{t("applications.reminder.notSent")}</p>
    </article>
  );
}
