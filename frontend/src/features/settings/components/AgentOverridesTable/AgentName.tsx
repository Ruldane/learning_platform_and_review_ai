import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";

/** Le nom de l'agent et son rôle ; un agent que le serveur ne connaît plus est signalé. */
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
