import { t } from "@/shared/i18n/t";
import type { LineView } from "../viewTypes";
import { Field } from "./Field";
import { Section } from "./Section";

interface TextLineSectionProps {
  kind: "title" | "summary";
  line: LineView | null;
  onChange: (line: LineView | null) => void;
}

/** The professional title (one line) or the summary (one paragraph); empty text removes it. */
export function TextLineSection({ kind, line, onChange }: TextLineSectionProps) {
  return (
    <Section title={t(`cv.profile.section.${kind}`)} path={kind}>
      <Field
        path={`${kind}.text`}
        label={t(kind === "title" ? "cv.profile.titleText" : "cv.profile.summaryText")}
        value={line?.text ?? ""}
        multiline={kind === "summary"}
        onChange={(text) => onChange({ ...line, id: line?.id ?? "", text })}
      />
    </Section>
  );
}
