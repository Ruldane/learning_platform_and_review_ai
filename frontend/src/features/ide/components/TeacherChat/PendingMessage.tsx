/** The question being sent stays dimmed on the right until the server returns it. */
export function PendingMessage({ text }: { text: string }) {
  return (
    <li className="flex justify-end">
      <p className="max-w-[90%] rounded-2xl bg-accent px-3 py-2 text-sm whitespace-pre-wrap text-accent-foreground opacity-70">
        {text}
      </p>
    </li>
  );
}
