import { t } from "@/shared/i18n/t";
import type { Proof, Transfer } from "./api";
import type { ProofChoice, TransferAction, TransferView } from "./components/viewTypes";

export function proofChoice(proof: Proof): ProofChoice {
  return {
    id: proof.id,
    label: t("skillTransfer.proofOption", { skill: proof.skill_name, proof: proof.label }),
  };
}

function actionOf(row: Transfer): TransferAction {
  if (row.assessment) {
    const assessment = row.assessment;
    return {
      kind: "result",
      result: {
        demonstrated: assessment.verdict === "demonstrated",
        date: assessment.assessed_at,
        feedback: assessment.feedback,
        criteria: assessment.criteria.map((text, i) => ({
          text,
          demonstrated: assessment.met[i] === true,
        })),
      },
    };
  }
  if (row.exercise && (row.stage === "ready" || row.retry === "answer")) {
    return {
      kind: "answer",
      answer: {
        title: row.exercise.title,
        question: row.exercise.prompt,
        text: row.answer ?? "",
        retry: row.retry === "answer",
      },
    };
  }
  if (row.stage === "scheduled" || row.retry === "prepare") {
    return row.available
      ? { kind: "prepare", retry: row.retry === "prepare" }
      : { kind: "message", text: "waiting" };
  }
  return { kind: "message", text: row.stage === "grading" ? "grading" : "preparing" };
}

export function transferView(row: Transfer): TransferView {
  return {
    skill: row.proof.skill_name,
    proof: row.proof.label,
    dueOn: row.due_on,
    action: actionOf(row),
  };
}
