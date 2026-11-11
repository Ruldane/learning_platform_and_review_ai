import { useRef, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";

const TABS = ["file", "url", "text"] as const;
export type UploadTab = (typeof TABS)[number];

interface UploadTabsProps {
  tab: UploadTab;
  onChange: (tab: UploadTab) => void;
}

/** Les trois onglets d'import ; flèches gauche et droite : onglet voisin, focus suivi (WAI-ARIA). */
export function UploadTabs({ tab, onChange }: UploadTabsProps) {
  const refs = useRef<Partial<Record<UploadTab, HTMLButtonElement | null>>>({});

  const onKeyDown = (event: KeyboardEvent) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = TABS[(TABS.indexOf(tab) + step + TABS.length) % TABS.length]!;
    onChange(next);
    refs.current[next]?.focus();
  };

  return (
    <div
      role="tablist"
      aria-label={t("memory.upload.tabs")}
      onKeyDown={onKeyDown}
      className="flex gap-1 border-b border-border"
    >
      {TABS.map((name) => (
        <button
          key={name}
          ref={(node) => {
            refs.current[name] = node;
          }}
          type="button"
          role="tab"
          id={`upload-tab-${name}`}
          aria-selected={tab === name}
          aria-controls={`upload-panel-${name}`}
          tabIndex={tab === name ? 0 : -1}
          onClick={() => onChange(name)}
          className="-mb-px border-b-2 border-transparent px-3 py-1.5 text-sm font-medium outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring aria-selected:border-primary"
        >
          {t(`memory.upload.${name}`)}
        </button>
      ))}
    </div>
  );
}
