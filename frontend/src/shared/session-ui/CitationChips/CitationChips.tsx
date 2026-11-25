import { t } from "@/shared/i18n/t";
import type { Citation } from "@/shared/realtime/types";
import { webUrl } from "../webUrl";

interface CitationChipsProps {
  citations: Citation[];
}

const CHIP =
  "inline-flex size-6 items-center justify-center rounded-full border border-border bg-muted text-xs font-medium";
const LINK = `${CHIP} hover:border-primary hover:text-primary focus-visible:ring-3 focus-visible:ring-ring outline-none`;

/** Address to open: the web page (http or https), else the memory item; `null` if none. */
function targetOf(citation: Citation): string | null {
  const address = citation.url === null ? null : webUrl(citation.url);
  if (address) return address.href;
  if (citation.memory_item_id) {
    return `/memory?item=${encodeURIComponent(citation.memory_item_id)}`;
  }
  return null;
}

/**
 * Numbered chips for an agent message's sources (SPEC 9.3): « 1 », « 2 »… A web page
 * opens in a new tab; a memory item opens the memory (also in a new tab: the current debate
 * stays open). An address that is not http(s) is never a link.
 */
export function CitationChips({ citations }: CitationChipsProps) {
  if (citations.length === 0) return null;
  const ordered = [...citations].sort((a, b) => a.index - b.index);
  return (
    <ul aria-label={t("session.citations.label")} className="mt-2 flex flex-wrap gap-1.5">
      {ordered.map((citation) => {
        const title =
          citation.title.trim() === "" ? t("session.citations.untitled") : citation.title;
        const name = t("session.citations.source", { index: citation.index, title });
        const href = targetOf(citation);
        return (
          <li key={citation.index}>
            {href ? (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={name}
                title={title}
                className={LINK}
              >
                {citation.index}
              </a>
            ) : (
              <span role="img" aria-label={name} title={title} className={CHIP}>
                {citation.index}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
