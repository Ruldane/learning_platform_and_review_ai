import { DebateFeed, InterruptCard } from "@/shared/session-ui";
import type { FeedItems } from "../viewTypes";
import { CaptureTextCard } from "./CaptureTextCard";

/** The question for an unreadable link, asking for its text (contract: `capture_text`). */
const CAPTURE_TEXT = "capture_text";

interface CaptureFeedProps {
  items: FeedItems;
  /** Is the `interruptId` question still waiting for an answer? */
  isAwaiting: (interruptId: string) => boolean;
  /** An answer is on its way: the cards are disabled. */
  pending: boolean;
  onAnswer: (interruptId: string, value: unknown) => void;
  /** The pasted text draft (`capture_text`), kept when the dialog closes. */
  textDraft: string;
  onTextDraft: (text: string) => void;
}

/**
 * The thread of a capture: the Archivist's summary lines and concepts, then its questions.
 * `capture_text`: a text area (unreadable link); `capture_task` and `capture_cards`: yes or
 * no, through the shared card.
 */
export function CaptureFeed(props: CaptureFeedProps) {
  const { items, isAwaiting, pending, onAnswer, textDraft, onTextDraft } = props;
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
            draft={textDraft}
            onDraft={onTextDraft}
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
