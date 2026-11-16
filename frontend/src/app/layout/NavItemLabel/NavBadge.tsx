interface NavBadgeProps {
  /** Le libellé de l'entrée (« Relances »). */
  name: string;
  useBadge: () => number | undefined;
  label: (count: number) => string;
}

/**
 * Le libellé d'une entrée de navigation avec sa pastille : le libellé et le nombre sont visibles,
 * et un seul texte pour les lecteurs d'écran, d'un seul tenant (« Relances, 3 relances dues »),
 * pour qu'aucun espace ne s'insère avant la virgule. Le libellé seul tant que le nombre est
 * inconnu ou nul.
 */
export function NavBadge({ name, useBadge, label }: NavBadgeProps) {
  const count = useBadge();
  if (!count || count <= 0) return <>{name}</>;
  return (
    <>
      <span className="sr-only">{`${name}, ${label(count)}`}</span>
      <span aria-hidden="true">{name}</span>
      <span
        aria-hidden="true"
        className="ml-auto min-w-5 rounded-full bg-primary px-1.5 text-center text-xs font-semibold text-primary-foreground tabular-nums"
      >
        {count}
      </span>
    </>
  );
}
