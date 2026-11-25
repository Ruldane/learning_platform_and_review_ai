import { cn } from "@/shared/lib/utils";

interface SwitchRowProps {
  /** The setting's name, read by the screen reader. */
  label: string;
  /** The state in full words, next to the switch (never carried by color alone). */
  stateText: string;
  checked: boolean;
  /** A save is in progress: the setting stays put until the response (focus stays). */
  pending: boolean;
  hint?: string;
  onToggle: () => void;
}

/** A switch: a `role="switch"` button with its written state and optional help. */
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
