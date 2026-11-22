import { useContext, useId } from "react";
import { t } from "@/shared/i18n/t";
import {
  RUN_SOURCES,
  RunSourceAvailability,
  useRunSource,
  type RunSource,
} from "@/shared/lib/runSource";

const API_SOURCES: ReadonlySet<RunSource> = new Set(["anthropic", "glm", "openai"]);

interface LaunchSourceMenuProps {
  value: RunSource | undefined;
  onChange: (value: RunSource | undefined) => void;
  describedBy?: string;
}

export function LaunchSourceMenu({ value, onChange, describedBy }: LaunchSourceMenuProps) {
  const id = useId();
  const [global] = useRunSource();
  const keys = useContext(RunSourceAvailability);
  return (
    <div className="flex flex-col gap-1 self-start">
      <label htmlFor={id} className="text-sm font-medium">
        {t("session.runSource.launchLabel")}
      </label>
      <select
        id={id}
        aria-describedby={describedBy}
        value={value ?? ""}
        onChange={(event) => onChange(RUN_SOURCES.find((source) => source === event.target.value))}
        className="rounded-md border border-border bg-background px-2 py-1 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <option value="">
          {t("session.runSource.global", { source: t(`session.runSource.options.${global}`) })}
        </option>
        {RUN_SOURCES.map((source) => {
          const missing = keys !== undefined && API_SOURCES.has(source) && !keys.has(source);
          return (
            <option key={source} value={source} disabled={missing && source !== value}>
              {t(`session.runSource.options.${source}`)}
              {missing ? ` ${t("session.runSource.noKey")}` : ""}
            </option>
          );
        })}
      </select>
    </div>
  );
}
