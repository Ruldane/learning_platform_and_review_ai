import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";

/** The agent's name and role; an agent the server no longer knows is flagged. */
export function AgentName({ name, known }: { name: string; known: boolean }) {
  const identity = agentIdentity(name);
  return (
    <>
      {identity.name}
      {identity.role ? (
        <span className="block font-normal text-muted-foreground">{identity.role}</span>
      ) : null}
      {known ? null : (
        <span className="block font-normal text-destructive">
          {t("settings.agents.unknownAgent")}
        </span>
      )}
    </>
  );
}
