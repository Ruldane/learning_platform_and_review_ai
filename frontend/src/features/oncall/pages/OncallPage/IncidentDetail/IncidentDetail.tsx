import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { IncidentClock } from "../../../components/IncidentClock";
import { IncidentJournal } from "../../../components/IncidentJournal";
import { IncidentRepair } from "../../../components/IncidentRepair";
import type { Activity, Incident } from "../../../types";
import { IncidentReportSection } from "../IncidentReportSection";

interface IncidentDetailProps {
  incident: Incident;
  busy: boolean;
  onAct: (activity: Activity) => void;
}

function eventDetail(event: Incident["events"][number]) {
  if (event.kind === "diagnostic") {
    return t(event.value === 1 ? "oncall.diagnosisOk" : "oncall.diagnosisFailed");
  }
  return t(`oncall.metric.${event.metric}`, { value: event.value });
}

export function IncidentDetail({ incident, busy, onAct }: IncidentDetailProps) {
  const state = incident.diagnostic.state;
  const events = incident.events.map((event) => ({
    id: event.id,
    minute: event.minute,
    detail: eventDetail(event),
  }));
  return (
    <>
      <Link to="/astreinte" className="self-start text-sm underline underline-offset-2">
        {t("oncall.back")}
      </Link>
      <h1 className="text-2xl font-semibold">{incident.title}</h1>
      <IncidentClock
        minute={incident.minute}
        ended={incident.minute >= 12}
        alerted={incident.alerted}
        busy={busy}
        onAdvance={() => onAct({ kind: "advance" })}
      />
      <IncidentJournal
        events={events}
        observed={incident.observed_events}
        busy={busy}
        onObserve={(eventId) => onAct({ kind: "observe", eventId })}
      />
      {incident.alerted && (
        <>
          <IncidentRepair
            projectUrl={`/code/${encodeURIComponent(incident.ide_session_id)}`}
            status={t(`oncall.diagnostic.${state}`)}
            busy={busy || state === "running"}
            onDiagnose={() => onAct({ kind: "diagnostic" })}
          />
          <IncidentReportSection
            key={incident.id}
            incident={incident}
            busy={busy}
            onReport={(text) => onAct({ kind: "report", text })}
          />
        </>
      )}
    </>
  );
}
