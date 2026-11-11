/** Un chiffre clé : libellé et valeur (à placer dans une liste de description). */
export function StatFigure({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col rounded-lg border border-border bg-card px-3 py-2">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-xl font-semibold">{value}</dd>
    </div>
  );
}
