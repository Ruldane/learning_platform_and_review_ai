import { t } from "@/shared/i18n/t";
import { todayString } from "../../dates";
import type { ConfirmationView } from "../../types";

/**
 * La question de confirmation reposée après une réponse que le serveur n'a pas pu prendre : ce que
 * January avait laissé dans les champs passe avant le brouillon du serveur, et une ligne dit
 * pourquoi (la date dans le futur, le cas que le client peut reconnaître, sinon un message général).
 * Sans réponse précédente (première question), la fiche telle que l'Assistant l'a lue.
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
