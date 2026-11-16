import { CheckCircle2, Circle, XCircle } from "lucide-react";

/** La pastille d'un critère : décorative, « Atteint » ou « Non atteint » est toujours écrit à côté. */
export function Mark({ met }: { met: boolean | null }) {
  const cls = "mt-0.5 size-4 shrink-0";
  if (met === null) return <Circle aria-hidden="true" className={`${cls} text-muted-foreground`} />;
  return met ? (
    <CheckCircle2 aria-hidden="true" className={`${cls} text-emerald-700 dark:text-emerald-400`} />
  ) : (
    <XCircle aria-hidden="true" className={`${cls} text-destructive`} />
  );
}
