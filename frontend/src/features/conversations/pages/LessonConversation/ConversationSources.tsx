import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { ConversationTurn } from "../../api";

export function ConversationSources({ sources }: Pick<ConversationTurn, "sources">) {
  if (!sources.length) return null;
  return (
    <ul className="mt-2 flex flex-col gap-1 text-sm" aria-label={t("conversations.sources")}>
      {sources.map(({ kind, id, title }) => {
        const key = encodeURIComponent(id);
        const path = kind === "lesson" ? `/apprendre/lecons/${key}` : `/memoire?item=${key}`;
        return (
          <li key={`${kind}:${id}`}>
            <Link to={path} className="underline">
              {title}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
