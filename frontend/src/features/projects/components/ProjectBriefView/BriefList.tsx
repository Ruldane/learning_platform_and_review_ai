interface BriefListProps {
  title: string;
  items: string[];
  ordered?: boolean;
}

/** A brief section that is a list; nothing renders when it is empty. */
export function BriefList({ title, items, ordered = false }: BriefListProps) {
  if (items.length === 0) return null;
  const List = ordered ? "ol" : "ul";
  return (
    <section className="flex flex-col gap-1">
      <h3 className="font-medium">{title}</h3>
      <List className={`flex flex-col gap-1 pl-5 ${ordered ? "list-decimal" : "list-disc"}`}>
        {items.map((item, index) => (
          <li key={`${index}-${item}`}>{item}</li>
        ))}
      </List>
    </section>
  );
}
