interface NavBadgeProps {
  /** The entry label (« Relances »). */
  name: string;
  useBadge: () => number | undefined;
  label: (count: number) => string;
}

/**
 * An entry label with its badge: the label and the count are visible,
 * and one text for screen readers, in one piece (« Relances, 3 relances dues »),
 * so no space is inserted before the comma. The label alone while the count is
 * unknown or zero.
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
