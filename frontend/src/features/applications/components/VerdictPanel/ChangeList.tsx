import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";
import type { ChangeView } from "../viewTypes";

/** Unsupported proper nouns require a check. Older saved suggestions can use the French tag. */
const isCheck = (change: ChangeView) =>
  change.text.startsWith("To check") || change.text.startsWith("À vérifier");

/**
 * Les changements proposés, dans l'ordre du comité. Un changement qui demande une compétence absente
 * du profil est marqué « À acquérir » : ce n'est jamais une ligne à ajouter au CV.
 */
export function ChangeList({ changes }: { changes: ChangeView[] }) {
  if (changes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t("applications.verdictPanel.changesEmpty")}</p>
    );
  }
  return (
    <ol className="flex list-decimal flex-col gap-3 pl-6">
      {changes.map((change, index) => {
        const check = isCheck(change);
        return (
          <li key={index} className="flex flex-col items-start gap-1">
            {change.needsSkill ? (
              <span className="rounded-md border border-dashed px-1.5 py-0.5 text-xs font-semibold">
                {t(
                  check
                    ? "applications.verdictPanel.needsCheck"
                    : "applications.verdictPanel.needsSkill",
                )}
              </span>
            ) : null}
            <p>{change.text}</p>
            {change.needsSkill && !check && change.terms.length > 0 ? (
              <p className="text-sm">
                {t("applications.verdictPanel.needsSkillTerms", { terms: change.terms.join(", ") })}
              </p>
            ) : null}
            <p className="text-sm text-muted-foreground">
              {t("applications.verdictPanel.changeBy", {
                name: agentIdentity(change.persona).name,
              })}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
