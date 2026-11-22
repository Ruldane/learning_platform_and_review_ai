import { useEffect, useRef } from "react";

export function RunLog({ label, output }: { label: string; output: string }) {
  const scroll = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [output]);
  return (
    <pre
      ref={scroll}
      role="log"
      aria-label={label}
      tabIndex={0}
      className="max-h-52 min-h-16 overflow-auto rounded bg-muted p-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"
    >
      {output}
    </pre>
  );
}
