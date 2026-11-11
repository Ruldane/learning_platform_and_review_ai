import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface DomainChipsProps {
  domains: string[];
  onRemove: (domain: string) => void;
}

/** Les domaines de la liste, un bouton de retrait chacun ; « Aucun domaine. » si elle est vide. */
export function DomainChips({ domains, onRemove }: DomainChipsProps) {
  if (domains.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("settings.search.domains.empty")}</p>;
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {domains.map((domain) => (
        <li
          key={domain}
          className="flex items-center gap-1 rounded-lg border border-border bg-secondary py-0.5 pr-0.5 pl-2.5 text-sm"
        >
          {domain}
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            aria-label={t("settings.search.domains.remove", { domain })}
            onClick={() => onRemove(domain)}
          >
            <span aria-hidden="true">×</span>
          </Button>
        </li>
      ))}
    </ul>
  );
}
