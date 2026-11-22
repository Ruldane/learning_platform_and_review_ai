import { useRef } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";

interface FileTabsProps {
  names: string[];
  current: string;
  entry: string;
  /** Les fichiers que Claude a modifiés : signalés en toutes lettres. */
  changed?: string[];
  onOpen: (name: string) => void;
  onClose?: (name: string) => void;
}

function tabLabel(name: string, entry: string, changed: string[]): string {
  const shown = name === entry ? t("ide.session.entryFile", { name }) : name;
  return changed.includes(name) ? t("ide.claude.changedTab", { name: shown }) : shown;
}

/** Les fichiers de la séance : un bouton par fichier, celui d'entrée est signalé en texte. */
export function FileTabs({ names, current, entry, changed = [], onOpen, onClose }: FileTabsProps) {
  const container = useRef<HTMLElement>(null);
  if (names.length <= 1 && onClose === undefined) return null;
  function close(name: string) {
    onClose?.(name);
    requestAnimationFrame(() => {
      const navigation = container.current;
      const active = navigation?.querySelector<HTMLButtonElement>('button[aria-current="true"]');
      (active ?? navigation)?.focus();
    });
  }
  return (
    <nav ref={container} tabIndex={-1} aria-label={t("ide.session.files")}>
      <ul className="flex flex-wrap gap-1">
        {names.map((name) => (
          <li key={name} className="flex items-center">
            <button
              type="button"
              aria-current={name === current ? "true" : undefined}
              onClick={() => onOpen(name)}
              className={cn(
                "rounded-lg border border-border px-2.5 py-1 text-sm outline-none",
                "focus-visible:ring-3 focus-visible:ring-ring",
                name === current ? "bg-muted font-medium" : "bg-background",
              )}
            >
              {tabLabel(name, entry, changed)}
            </button>
            {onClose && names.length > 1 ? (
              <button
                type="button"
                aria-label={t("ide.project.closeTab", { name })}
                className="px-1 focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => close(name)}
              >
                ×
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </nav>
  );
}
