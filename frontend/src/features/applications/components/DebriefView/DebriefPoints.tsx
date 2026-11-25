/** A titled debrief list (strengths, points to fix). */
export function DebriefPoints({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="flex flex-col gap-1">
      <h3 className="text-lg font-semibold">{title}</h3>
      <ul className="list-disc pl-5">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
