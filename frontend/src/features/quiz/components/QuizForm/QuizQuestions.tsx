import type { QuestionView } from "../viewTypes";
import { QuestionField } from "./QuestionField";
import type { Given } from "./useQuizAnswers";

interface Props {
  questions: QuestionView[];
  given: (id: string) => Given;
  disabled: boolean;
  onAnswer: (id: string, patch: Partial<Given>) => void;
}

export function QuizQuestions({ questions, given, disabled, onAnswer }: Props) {
  return (
    <ol className="flex flex-col gap-3">
      {questions.map((question) => (
        <QuestionField
          key={question.id}
          question={question}
          choice={given(question.id).choice}
          text={given(question.id).text}
          disabled={disabled}
          onChoice={(choice) => onAnswer(question.id, { choice })}
          onText={(text) => onAnswer(question.id, { text })}
        />
      ))}
    </ol>
  );
}
