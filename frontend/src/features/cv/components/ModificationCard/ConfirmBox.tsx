import { useId } from "react";
import { t } from "@/shared/i18n/t";

interface ConfirmBoxProps {
  /** What is not in the profile: a figure, a tool, a title. */
  blocks: string[];
  confirmed: boolean;
  onChange: (confirmed: boolean) => void;
  disabled: boolean;
}

/**
 * The « À confirmer » box: what the profile lacks, and the one checkbox that allows accepting.
 */
export function ConfirmBox({ blocks, confirmed, onChange, disabled }: ConfirmBoxProps) {
  const id = useId();
  return (
    <div
      role="group"
      aria-labelledby={`${id}-title`}
      className="flex flex-col gap-2 rounded-lg border-2 border-foreground/60 bg-muted/60 p-3 text-sm"
    >
      <h4 id={`${id}-title`} className="font-semibold">
        {t("cv.mod.confirmTitle")}
      </h4>
      <p>{t("cv.mod.confirmIntro")}</p>
      {blocks.length > 0 ? (
        <ul className="list-disc pl-5">
          {blocks.map((block, index) => (
            <li key={index}>{block}</li>
          ))}
        </ul>
      ) : null}
      <label className="flex items-center gap-2 font-medium">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
          className="size-4"
        />
        {t("cv.mod.confirmBox")}
      </label>
    </div>
  );
}
