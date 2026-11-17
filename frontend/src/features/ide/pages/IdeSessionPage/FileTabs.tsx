import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";

interface FileTabsProps {
  names: string[];
  current: string;
  entry: string;
  onOpen: (name: string) => void;
}

/** Les fichiers de la séance : un bouton par fichier, celui d'entrée est signalé en texte. */
export function FileTabs({ names, current, entry, onOpen }: FileTabsProps) {
  if (names.length <= 1) return null;
  return (
    <nav aria-label={t("ide.session.files")}>
      <ul className="flex flex-wrap gap-1">
        {names.map((name) => (
          <li key={name}>
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
              {name === entry ? t("ide.session.entryFile", { name }) : name}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
