interface NavBadgeProps {
  useBadge: () => number | undefined;
  label: (count: number) => string;
}

/**
 * La pastille d'une entrée de navigation : le nombre, visible, et son texte pour les lecteurs
 * d'écran (« 3 relances dues »). Rien tant que le nombre est inconnu ou nul.
 */
export function NavBadge({ useBadge, label }: NavBadgeProps) {
  const count = useBadge();
  if (!count || count <= 0) return null;
  return (
    <>
      <span
        aria-hidden="true"
        className="ml-auto min-w-5 rounded-full bg-primary px-1.5 text-center text-xs font-semibold text-primary-foreground tabular-nums"
      >
        {count}
      </span>
      <span className="sr-only">{`, ${label(count)}`}</span>
    </>
  );
}
