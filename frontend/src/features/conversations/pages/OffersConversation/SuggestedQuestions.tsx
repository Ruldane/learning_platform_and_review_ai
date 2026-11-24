import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

const SUGGESTIONS = ["dates", "applied", "contacts", "skills"] as const;

export function SuggestedQuestions({ onSelect }: { onSelect: (question: string) => void }) {
  return (
    <div
      role="group"
      aria-label={t("conversations.offers.suggestions")}
      className="flex flex-wrap gap-2 p-3"
    >
      {SUGGESTIONS.map((suggestion) => {
        const question = t(`conversations.offers.${suggestion}`);
        return (
          <Button
            key={suggestion}
            type="button"
            variant="outline"
            size="sm"
            className="h-auto whitespace-normal"
            onClick={() => onSelect(question)}
          >
            {question}
          </Button>
        );
      })}
    </div>
  );
}
