import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { ConversationTurn } from "../../api";

const paths = {
  lesson: (id: string) => `/apprendre/lecons/${id}`,
  memory: (id: string) => `/memoire?item=${id}`,
  posting: (id: string) => `/career/postings/${id}`,
  application: (id: string) => `/candidatures/${id}`,
} satisfies Record<ConversationTurn["sources"][number]["kind"], (id: string) => string>;

export function ConversationSources({ sources }: Pick<ConversationTurn, "sources">) {
  if (!sources.length) return null;
  return (
    <ul className="mt-2 flex flex-col gap-1 text-sm" aria-label={t("conversations.sources")}>
      {sources.map(({ kind, id, title }) => {
        const path = paths[kind](encodeURIComponent(id));
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
