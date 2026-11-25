import { t } from "@/shared/i18n/t";
import { todayString } from "../../dates";
import type { ConfirmationView } from "../../types";

/**
 * The confirmation question asked again after an answer the server could not take: what
 * January left in the fields comes before the server's draft, and a line says
 * why (a future date, a case the client can recognise, or else a general message).
 * With no previous answer (first question), the record as the Assistant read it.
 */
export function asReasked(
  view: ConfirmationView,
  sent: Record<string, string> | null,
): ConfirmationView {
  if (sent === null) return view;
  const future = (sent.applied_on ?? "") > todayString();
  return {
    ...view,
    fields: view.fields.map((field) => ({ ...field, value: sent[field.id] ?? field.value })),
    reason: t(future ? "applications.confirm.reasonFuture" : "applications.confirm.reasonGeneric"),
  };
}
