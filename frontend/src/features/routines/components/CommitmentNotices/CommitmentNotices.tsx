import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

interface Notice {
  id: string;
  title: string;
  version: string;
  intention: string;
  due_on: string;
  indicator: string;
  unit: string;
  delta?: number | string | null;
}

const dateLabel = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeZone: "UTC" });

export function CommitmentNotices({ notices }: { notices: readonly Notice[] }) {
  if (!notices.length) return null;
  return (
    <ul className="mt-2 grid gap-2">
      {notices.map((notice) => (
        <li className="border-l pl-3" key={notice.id}>
          <Link
            className="font-medium underline"
            to={`/etudier/engagements/${encodeURIComponent(notice.id)}`}
          >
            {notice.title}
          </Link>
          <p className="text-sm">
            {t("routines.commitmentDate", {
              version: notice.version,
              date: dateLabel.format(new Date(`${notice.due_on}T00:00:00Z`)),
            })}
          </p>
          <p className="break-words">{notice.intention}</p>
          <p className="text-sm">{notice.indicator}</p>
          {notice.delta != null && (
            <p>{t("routines.commitmentDelta", { value: notice.delta, unit: notice.unit })}</p>
          )}
        </li>
      ))}
    </ul>
  );
}
