import { ChevronDown } from "lucide-react";
import type { KeyboardEvent, Ref } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { NavGroup } from "../../buildNav";
import { SumBadges } from "../SumBadges";
import { SumLabel } from "../SumLabel";

interface SectionButtonProps {
  group: NavGroup;
  /** La page courante est dans cette section. */
  active: boolean;
  open: boolean;
  onToggle: () => void;
  onKeyDown: (event: KeyboardEvent) => void;
  ref: Ref<HTMLButtonElement>;
}

/** Le bouton d'une section : icône, nom (avec la somme des pastilles), flèche. */
export function SectionButton(props: SectionButtonProps) {
  const { group, active, open, onToggle, onKeyDown, ref } = props;
  const Icon = group.icon;
  return (
    <button
      ref={ref}
      type="button"
      aria-haspopup="true"
      aria-expanded={open}
      aria-current={active ? "true" : undefined}
      data-active={active ? "true" : undefined}
      onClick={onToggle}
      onKeyDown={onKeyDown}
      className={cn(
        "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap hover:bg-muted",
        active || open ? "bg-accent text-accent-foreground" : "text-foreground",
      )}
    >
      <Icon aria-hidden="true" className="size-4" />
      <SumBadges items={group.items}>
        {(parts) => <SumLabel name={t(group.labelKey)} parts={parts} />}
      </SumBadges>
      <ChevronDown aria-hidden="true" className="size-4 text-muted-foreground" />
    </button>
  );
}
