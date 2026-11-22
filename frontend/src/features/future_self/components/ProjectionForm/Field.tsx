import type { ComponentProps } from "react";

const input =
  "min-w-0 rounded-md border border-input bg-background p-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function Field({ label, ...props }: ComponentProps<"input"> & { label: string }) {
  return (
    <label className="grid gap-1 text-sm font-medium">
      {label}
      <input className={input} {...props} />
    </label>
  );
}
