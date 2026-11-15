import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";
import type { ObjectionView } from "../viewTypes";

/** Les objections classées (la première est la plus importante), avec ceux qui les soulèvent. */
export function ObjectionList({ objections }: { objections: ObjectionView[] }) {
  if (objections.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {t("applications.verdictPanel.objectionsEmpty")}
      </p>
    );
  }
  return (
    <ol className="flex list-decimal flex-col gap-2 pl-6">
      {objections.map((objection) => (
        <li key={objection.text}>
          <p>{objection.text}</p>
          <p className="text-sm text-muted-foreground">
            {t("applications.verdictPanel.raisedBy", {
              names: objection.personas.map((persona) => agentIdentity(persona).name).join(", "),
            })}
          </p>
        </li>
      ))}
    </ol>
  );
}
