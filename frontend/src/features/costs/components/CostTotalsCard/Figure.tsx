import type { ReactNode } from "react";

/** Un chiffre du total : son nom (`dt`) et sa valeur (`dd`). */
export function Figure({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-2xl font-semibold tabular-nums">{children}</dd>
    </div>
  );
}
