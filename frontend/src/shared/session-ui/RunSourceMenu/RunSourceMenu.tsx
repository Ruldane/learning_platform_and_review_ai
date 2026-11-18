import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { RUN_SOURCES, type RunSource } from "@/shared/lib/runSource";

interface RunSourceMenuProps {
  value: RunSource;
  onChange: (value: RunSource) => void;
  /** Fournisseurs d'API dont une clé est enregistrée ; les autres sont grisés. */
  keyed: ReadonlySet<string>;
  /** Panneau : libellé court ; page de réglages : avec l'explication. */
  detailed?: boolean;
}

const API_SOURCES: ReadonlySet<RunSource> = new Set(["anthropic", "glm", "openai"]);

/** Le menu « Qui fait tourner les agents » : réglages, client MCP ou API d'un fournisseur. */
export function RunSourceMenu({ value, onChange, keyed, detailed = false }: RunSourceMenuProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("session.runSource.label")}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value as RunSource)}
        className="rounded-md border border-border bg-background px-2 py-1 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        {RUN_SOURCES.map((source) => {
          const missing = API_SOURCES.has(source) && !keyed.has(source);
          return (
            <option key={source} value={source} disabled={missing && source !== value}>
              {t(`session.runSource.options.${source}`)}
              {missing ? ` ${t("session.runSource.noKey")}` : ""}
            </option>
          );
        })}
      </select>
      {detailed ? (
        <p className="text-sm text-muted-foreground">{t(`session.runSource.help.${value}`)}</p>
      ) : null}
    </div>
  );
}
