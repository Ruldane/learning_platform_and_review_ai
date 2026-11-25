import { useRef } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ReminderCard } from "../../components/ReminderCard";
import { useReminderHandlers } from "../../hooks/useReminderHandlers";
import { useReminders } from "../../hooks/useReminders";
import { BOARD_PATH } from "../../urls";

/**
 * Les relances dues (`/applications/reminders`) : qui contacter, le brouillon à copier, puis Fait,
 * Reporter de 3 jours ou Ignorer (« Classer en Sans réponse » pour la dernière relance). Rien n'est
 * envoyé par l'application. Une relance traitée disparaît de la liste, annoncée dans une zone
 * vocale ; le focus revient alors sur le titre de la page, au-dessus de la liste.
 */
export function RemindersPage() {
  const navigate = useNavigate();
  const query = useReminders();
  const heading = useRef<HTMLHeadingElement>(null);
  const reminders = query.data ?? [];
  const handlers = useReminderHandlers(reminders, () => heading.current?.focus());

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold outline-none">
          {t("applications.remindersPage.title")}
        </h1>
        <p className="text-muted-foreground">{t("applications.remindersPage.intro")}</p>
      </header>
      <p role="status" className="min-h-5 text-sm text-muted-foreground">
        {handlers.message}
      </p>
      {handlers.error ? <InlineError message={handlers.error} /> : null}
      {query.isPending ? <LoadingState label={t("applications.remindersPage.loading")} /> : null}
      {query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && reminders.length === 0 ? (
        <EmptyState
          title={t("applications.remindersPage.emptyTitle")}
          description={t("applications.remindersPage.emptyDescription")}
          action={{
            label: t("applications.remindersPage.emptyAction"),
            onClick: () => void navigate(BOARD_PATH),
          }}
        />
      ) : null}
      {reminders.length > 0 ? (
        <ul aria-label={t("applications.remindersPage.listLabel")} className="flex flex-col gap-3">
          {reminders.map((reminder) => (
            <li key={reminder.id}>
              <ReminderCard reminder={reminder} {...handlers.cardProps} />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
