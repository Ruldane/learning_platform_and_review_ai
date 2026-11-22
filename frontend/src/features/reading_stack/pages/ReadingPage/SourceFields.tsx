import type { Ref } from "react";
import { t } from "@/shared/i18n/t";
import type { ReadingSourceInput } from "../../api";

const kinds = ["topic", "site", "rss"] as const;
const labels = { topic: "valueTopic", site: "valueSite", rss: "valueFeed" } as const;
const inputClass = "rounded-md border bg-background p-2";
const labelClass = "flex flex-col gap-1 text-sm";

interface SourceFieldsProps {
  value: ReadingSourceInput;
  onChange: (value: ReadingSourceInput) => void;
  labelRef: Ref<HTMLInputElement>;
}

export function SourceFields({ value, onChange, labelRef }: SourceFieldsProps) {
  const { kind, label } = value;
  return (
    <>
      <label className={labelClass}>
        {t("reading.sources.kind")}
        <select
          className={inputClass}
          value={kind}
          onChange={(event) => {
            const kind = kinds.find((choice) => choice === event.target.value);
            if (kind) onChange({ ...value, kind });
          }}
        >
          {kinds.map((choice) => (
            <option key={choice} value={choice}>
              {t(`reading.sources.${choice}`)}
            </option>
          ))}
        </select>
      </label>
      <label className={labelClass}>
        {t("reading.sources.label")}
        <input
          ref={labelRef}
          className={inputClass}
          required
          maxLength={100}
          value={label}
          onChange={(event) => onChange({ ...value, label: event.target.value })}
        />
      </label>
      <label className={`${labelClass} sm:col-span-2`}>
        {t(`reading.sources.${labels[kind]}`)}
        <input
          className={inputClass}
          required
          maxLength={kind === "topic" ? 180 : 2000}
          type={kind === "rss" ? "url" : "text"}
          value={value.value}
          onChange={(event) => onChange({ ...value, value: event.target.value })}
        />
      </label>
    </>
  );
}
