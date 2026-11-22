import { useState } from "react";
import { RUN_SOURCES, type RunSource } from "@/shared/lib/runSource";

const keyOf = (identity: string) => `tremplin.conversation.source.${identity}`;

export function readConversationSource(identity: string): RunSource | undefined {
  try {
    const saved = localStorage.getItem(keyOf(identity));
    return RUN_SOURCES.find((value) => value === saved);
  } catch {
    return undefined;
  }
}

export function useConversationSource(identity: string) {
  const key = keyOf(identity);
  const [source, setSource] = useState(() => readConversationSource(identity));
  return [
    source,
    (choice: RunSource | undefined) => {
      setSource(choice);
      try {
        if (choice === undefined) localStorage.removeItem(key);
        else localStorage.setItem(key, choice);
      } catch {
        // Le choix reste valable tant que le panneau est ouvert.
      }
    },
  ] as const;
}
