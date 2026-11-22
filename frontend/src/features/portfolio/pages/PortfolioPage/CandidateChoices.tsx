import type { Site } from "../../api";

interface Props {
  candidates: Site["candidates"];
  selected: string[];
  busy: boolean;
  onToggle: (id: string) => void;
}

export function CandidateChoices({ candidates, selected, busy, onToggle }: Props) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {candidates.map((item) => {
        const checked = selected.includes(item.id);
        return (
          <label
            key={item.id}
            className="flex items-start gap-2 rounded-md border border-border p-3"
          >
            <input
              type="checkbox"
              className="mt-1"
              checked={checked}
              aria-label={item.label}
              disabled={busy || (selected.length >= 50 && !checked)}
              onChange={() => onToggle(item.id)}
            />
            <span className="min-w-0 break-words">
              <span className="block font-medium">{item.label}</span>
              {item.label !== item.text && <span className="block text-sm">{item.text}</span>}
              {item.url && <span className="block text-sm break-all">{item.url}</span>}
            </span>
          </label>
        );
      })}
    </div>
  );
}
