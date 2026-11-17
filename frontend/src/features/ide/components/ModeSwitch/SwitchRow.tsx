import { cn } from "@/shared/lib/utils";

interface SwitchRowProps {
  /** Le nom du réglage, lu par le lecteur d'écran. */
  label: string;
  /** L'état en toutes lettres, à côté de l'interrupteur (jamais porté par la seule couleur). */
  stateText: string;
  checked: boolean;
  /** Une écriture est en cours : le réglage ne bouge plus avant la réponse (le focus reste). */
  pending: boolean;
  hint?: string;
  onToggle: () => void;
}

/** Un interrupteur : bouton `role="switch"` avec son état écrit et une aide facultative. */
export function SwitchRow({ label, stateText, checked, pending, hint, onToggle }: SwitchRowProps) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-3">
        <button
          type="button"
          role="switch"
          aria-checked={checked}
          aria-disabled={pending}
          onClick={() => !pending && onToggle()}
          className={cn(
            "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border border-border outline-none transition-colors",
            "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring aria-disabled:opacity-50",
            checked ? "bg-primary" : "bg-muted",
          )}
        >
          <span className="sr-only">{label}</span>
          <span
            aria-hidden="true"
            className={cn(
              "size-4 rounded-full bg-background shadow transition-transform",
              checked ? "translate-x-6" : "translate-x-1",
            )}
          />
        </button>
        <span className="text-sm font-medium">{stateText}</span>
      </div>
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
