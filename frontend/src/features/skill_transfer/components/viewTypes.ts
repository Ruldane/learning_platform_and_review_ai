export interface ProofChoice {
  id: string;
  label: string;
}

export interface AnswerView {
  title: string;
  question: string;
  text: string;
  retry: boolean;
}

export interface ResultView {
  demonstrated: boolean;
  date: string;
  feedback: string;
  criteria: { text: string; demonstrated: boolean }[];
}

export type TransferAction =
  | { kind: "message"; text: "waiting" | "preparing" | "grading" }
  | { kind: "prepare"; retry: boolean }
  | { kind: "answer"; answer: AnswerView }
  | { kind: "result"; result: ResultView };

export interface TransferView {
  skill: string;
  proof: string;
  dueOn: string;
  action: TransferAction;
}
