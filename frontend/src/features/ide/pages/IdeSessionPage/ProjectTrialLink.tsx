import type { MouseEvent } from "react";
import { Link, useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";

export function ProjectTrialLink({
  sessionId,
  save,
}: {
  sessionId: string;
  save: () => Promise<boolean>;
}) {
  const navigate = useNavigate();
  const to = `/code/${encodeURIComponent(sessionId)}/trial`;
  async function open(event: MouseEvent<HTMLAnchorElement>) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
      return;
    event.preventDefault();
    if (await save()) await navigate(to);
  }
  return (
    <Link
      to={to}
      onClick={(event) => void open(event)}
      className="self-start text-sm underline underline-offset-4"
    >
      {t("codeTrial.title")}
    </Link>
  );
}
