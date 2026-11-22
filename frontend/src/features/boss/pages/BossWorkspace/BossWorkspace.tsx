import { Link } from "react-router";
import type { components } from "@/shared/api/schema";
import { t } from "@/shared/i18n/t";
import { useCountdown } from "../../hooks/useCountdown";
import { BossResults } from "../BossResults";
import { BossSubmission } from "../BossSubmission";

interface BossWorkspaceProps {
  attempt: components["schemas"]["BossAttemptOut"];
  receivedAt: number;
  sending: boolean;
  onSubmit: () => void;
}

function displayTime(seconds: number) {
  return [Math.floor(seconds / 60), seconds % 60]
    .map((unit) => String(unit).padStart(2, "0"))
    .join(":");
}

export function BossWorkspace({ attempt, receivedAt, sending, onSubmit }: BossWorkspaceProps) {
  const seconds = useCountdown(attempt.deadline_at, attempt.server_time, receivedAt);
  return (
    <>
      {(attempt.state === "building" || attempt.state === "expired") && (
        <p>
          {t("boss.timeLeft")}{" "}
          <time className="font-mono tabular-nums" dateTime={`PT${seconds}S`}>
            {displayTime(seconds)}
          </time>
        </p>
      )}
      <section aria-labelledby="boss-brief" className="flex flex-col gap-2">
        <h2 id="boss-brief" className="text-lg font-semibold">
          {t("boss.brief")}
        </h2>
        <p>{attempt.brief}</p>
      </section>
      {attempt.client_change ? (
        <section
          aria-labelledby="boss-change"
          className="flex flex-col gap-2 rounded-lg border border-border p-4"
        >
          <h2 id="boss-change" className="text-lg font-semibold">
            {t("boss.change")}
          </h2>
          <p role="status">{attempt.client_change.requirement}</p>
        </section>
      ) : (
        <p>{t("boss.waitChange")}</p>
      )}
      <Link
        className="underline underline-offset-2"
        to={`/code/${encodeURIComponent(attempt.ide_session_id)}`}
      >
        {t("boss.openIde")}
      </Link>
      <BossSubmission
        state={attempt.state}
        canSubmit={!!attempt.client_change && seconds > 0}
        sending={sending}
        onSubmit={onSubmit}
      />
      {attempt.grade && <BossResults grade={attempt.grade} proved={attempt.proof_recorded} />}
    </>
  );
}
