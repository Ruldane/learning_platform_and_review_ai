import type { BadgePart } from "../SumBadges";

/**
 * Le nom d'une section (ou du bouton « Menu ») avec la somme des pastilles de ses entrées. Le
 * texte lu par les lecteurs d'écran est d'un seul tenant (« Candidatures, 3 relances dues »).
 */
export function SumLabel({ name, parts }: { name: string; parts: BadgePart[] }) {
  if (parts.length === 0) return <>{name}</>;
  const total = parts.reduce((sum, part) => sum + part.count, 0);
  return (
    <>
      <span className="sr-only">{`${name}, ${parts.map((part) => part.text).join(", ")}`}</span>
      <span aria-hidden="true">{name}</span>
      <span
        aria-hidden="true"
        className="min-w-5 rounded-full bg-primary px-1.5 text-center text-xs font-semibold text-primary-foreground tabular-nums"
      >
        {total}
      </span>
    </>
  );
}
