interface ChipsProps {
  title: string;
  items: string[];
}

/** Une liste de mots (mots clés, outils, critères) en pastilles ; rien si elle est vide. */
export function Chips({ title, items }: ChipsProps) {
  if (items.length === 0) return null;
  return (
    <section className="flex flex-col gap-1">
      <h4 className="text-sm font-medium">{title}</h4>
      <ul className="flex flex-wrap gap-1.5">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="rounded-md bg-muted px-2 py-0.5 text-sm">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
