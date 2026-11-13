import { DebateFeed, InterruptCard } from "@/shared/session-ui";
import type { FeedItems } from "../viewTypes";
import { CaptureTextCard } from "./CaptureTextCard";

/** La question d'un lien illisible, qui demande le texte (le contrat l'appelle `capture_text`). */
const CAPTURE_TEXT = "capture_text";

interface CaptureFeedProps {
  items: FeedItems;
  /** La question `interruptId` attend-elle encore une réponse ? */
  isAwaiting: (interruptId: string) => boolean;
  /** Une réponse est en route : les cartes sont désactivées. */
  pending: boolean;
  onAnswer: (interruptId: string, value: unknown) => void;
}

/**
 * Le fil d'une capture : les lignes de résumé et les concepts de l'Archiviste, puis ses questions.
 * `capture_text` : une zone de texte (lien illisible) ; `capture_task` et `capture_cards` : oui ou
 * non, par la carte commune.
 */
export function CaptureFeed({ items, isAwaiting, pending, onAnswer }: CaptureFeedProps) {
  return (
    <DebateFeed
      items={items}
      renderInterrupt={({ interrupt, answered }) => {
        const disabled = pending || !isAwaiting(interrupt.interrupt_id);
        const answer = (value: unknown) => onAnswer(interrupt.interrupt_id, value);
        return interrupt.kind === CAPTURE_TEXT ? (
          <CaptureTextCard
            interrupt={interrupt}
            answered={answered}
            disabled={disabled}
            onAnswer={answer}
          />
        ) : (
          <InterruptCard
            interrupt={interrupt}
            answered={answered}
            disabled={disabled}
            onAnswer={answer}
          />
        );
      }}
    />
  );
}
