import { t } from "@/shared/i18n/t";
import { DuplicateAlert } from "@/shared/ui/DuplicateAlert";
import { InlineError } from "@/shared/ui/states/InlineError";
import { EventTimeline } from "../../components/EventTimeline";
import { StatusBadge } from "../../components/StatusBadge";
import { useUpdateApplication } from "../../hooks/useUpdateApplication";
import { toAlertView, toEventView, toReminderView } from "../../toView";
import type { AlertOut, ApplicationDetail } from "../../types";
import { AppliedAction } from "./AppliedAction";
import { DetailsForm } from "./DetailsForm";
import { DrawerReminders } from "./DrawerReminders";
import { DrawerSection } from "./DrawerSection";
import { NoteForm } from "./NoteForm";
import { PostingTextSection } from "./PostingTextSection";
import { StatusChange } from "./StatusChange";
import { ToolLinks } from "./ToolLinks";
import { useRecordMessage } from "./useRecordMessage";
import { VersionSection } from "./VersionSection";

interface DrawerBodyProps {
  detail: ApplicationDetail;
  /** The « même entreprise » info received when the record was created. */
  info: AlertOut[];
}

const nothing = () => undefined;

/**
 * The drawer content: editable info and contacts, « J'ai postulé », status change
 * dated, note, CV version, pending reminders, history and links to the kit, the interview
 * and the committee. Each write returns the re-read record; a live region says what just changed.
 */
export function DrawerBody({ detail, info }: DrawerBodyProps) {
  const update = useUpdateApplication(detail.id);
  const { message, recordAndSay, saveAndSay } = useRecordMessage(detail.status, update);
  const pending = detail.reminders.filter((reminder) => reminder.status === "pending");
  return (
    <div className="flex flex-col gap-4">
      <div>
        <StatusBadge status={detail.status} />
      </div>
      {info.length > 0 ? (
        // Information alone is a note: none of the three choices is shown.
        <DuplicateAlert
          alerts={info.map(toAlertView)}
          onOpen={nothing}
          onDistinct={nothing}
          onCancel={nothing}
        />
      ) : null}
      <p role="status" className="min-h-5 text-sm text-muted-foreground">
        {message}
      </p>
      {update.error ? <InlineError message={update.error} /> : null}
      <DrawerSection title={t("applications.drawer.detailsTitle")}>
        <DetailsForm key={detail.id} detail={detail} pending={update.pending} onSave={saveAndSay} />
      </DrawerSection>
      <DrawerSection title={t("applications.drawer.statusTitle")}>
        {detail.status === "to_apply" ? (
          <AppliedAction pending={update.pending} onRecord={recordAndSay} />
        ) : null}
        <StatusChange
          key={detail.status}
          current={detail.status}
          pending={update.pending}
          onRecord={recordAndSay}
        />
        <NoteForm pending={update.pending} onRecord={recordAndSay} />
      </DrawerSection>
      <PostingTextSection detail={detail} pending={update.pending} onSave={saveAndSay} />
      <VersionSection number={detail.cv_version_number} />
      <DrawerReminders reminders={pending.map(toReminderView)} />
      <DrawerSection title={t("applications.drawer.timelineTitle")}>
        <EventTimeline events={detail.events.map(toEventView)} />
      </DrawerSection>
      <ToolLinks
        applicationId={detail.id}
        hasScheduledInterview={detail.status === "interview" && Boolean(detail.interview_on)}
      />
    </div>
  );
}
