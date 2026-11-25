import type { KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";

export type PostingTab = "url" | "text";
export const POSTING_TABS: PostingTab[] = ["url", "text"];

interface PostingTabsProps {
  tab: PostingTab;
  /** The base `id` of each tab: `<id>-tab` for the tab, `<id>-panel` for its panel. */
  ids: Record<PostingTab, string>;
  onChange: (tab: PostingTab) => void;
}

/** The « Lien » and « Texte » tabs: left and right arrows move between them. */
export function PostingTabs({ tab, ids, onChange }: PostingTabsProps) {
  const move = (event: KeyboardEvent, from: PostingTab) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const count = POSTING_TABS.length;
    const next = POSTING_TABS[(POSTING_TABS.indexOf(from) + step + count) % count] ?? from;
    onChange(next);
    document.getElementById(`${ids[next]}-tab`)?.focus();
  };
  return (
    <div role="tablist" aria-label={t("gap.form.tabs")} className="flex gap-1 border-b">
      {POSTING_TABS.map((key) => (
        <button
          key={key}
          type="button"
          role="tab"
          id={`${ids[key]}-tab`}
          aria-selected={tab === key}
          aria-controls={`${ids[key]}-panel`}
          tabIndex={tab === key ? 0 : -1}
          onClick={() => onChange(key)}
          onKeyDown={(event) => move(event, key)}
          className="-mb-px border-b-2 border-transparent px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring aria-selected:border-primary"
        >
          {t(key === "url" ? "gap.form.tabUrl" : "gap.form.tabText")}
        </button>
      ))}
    </div>
  );
}
