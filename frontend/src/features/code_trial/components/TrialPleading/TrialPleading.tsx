import { useId } from "react";
interface TrialPleadingProps {
  roleLabel: string;
  argument: string;
  quotes: { id: string; label: string; code: string }[];
}

export function TrialPleading({ roleLabel, argument, quotes }: TrialPleadingProps) {
  const heading = useId();
  return (
    <section aria-labelledby={heading} className="grid gap-3 rounded-xl border bg-card p-4">
      <h2 id={heading} className="text-lg font-semibold">
        {roleLabel}
      </h2>
      <p className="whitespace-pre-wrap break-words">{argument}</p>
      {quotes.map(({ id, label, code }) => (
        <details key={id} className="rounded-md border p-2">
          <summary className="cursor-pointer break-words text-sm font-medium">{label}</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs">
            <code>{code}</code>
          </pre>
        </details>
      ))}
    </section>
  );
}
