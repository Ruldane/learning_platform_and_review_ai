import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { RUN_SOURCES, type RunSource } from "@/shared/lib/runSource";

interface RunSourceMenuProps {
  value: RunSource;
  onChange: (value: RunSource) => void;
  /** API providers with a saved key; the others are greyed out. */
  keyed: ReadonlySet<string>;
  /** Panel: short label; settings page: with the explanation. */
  detailed?: boolean;
}

const API_SOURCES: ReadonlySet<RunSource> = new Set(["anthropic", "glm", "openai"]);

/** The « Qui fait tourner les agents » menu: settings, the MCP client, or a provider's API. */
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
