import { t } from "@/shared/i18n/t";
import { Field } from "./Field";

export function CapacityFields({ target }: { target: number }) {
  return (
    <>
      <Field
        label={t("futureSelf.alternative")}
        type="number"
        name="hours"
        min={0}
        max={168}
        step={0.25}
      />
      <Field
        label={t("futureSelf.target")}
        type="number"
        name="target"
        min={1}
        max={100}
        defaultValue={target}
        required
      />
    </>
  );
}
