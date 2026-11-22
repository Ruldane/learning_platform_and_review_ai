import { useState } from "react";
import { RUN_SOURCES, type RunSource } from "@/shared/lib/runSource";

export function useConversationSource(identity: string) {
  const key = `tremplin.conversation.source.${identity}`;
  const [source, setSource] = useState<RunSource | undefined>(() => {
    try {
      const saved = localStorage.getItem(key);
      return RUN_SOURCES.find((value) => value === saved);
    } catch {
      return undefined;
    }
  });
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
