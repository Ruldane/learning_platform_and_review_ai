import { t } from "@/shared/i18n/t";
import type { IdentityView } from "../viewTypes";
import { Field } from "./Field";
import { Section } from "./Section";

interface IdentitySectionProps {
  identity: IdentityView;
  onChange: (identity: IdentityView) => void;
}

type OptionalKey = "email" | "phone" | "location" | "headline";
const OPTIONAL: OptionalKey[] = ["email", "phone", "location", "headline"];

/** Nom, e-mail, téléphone, lieu et accroche. */
export function IdentitySection({ identity, onChange }: IdentitySectionProps) {
  const set = (changes: Partial<IdentityView>) => onChange({ ...identity, ...changes });
  return (
    <Section title={t("cv.profile.section.identity")} path="identity" defaultOpen>
      <Field
        path="identity.name"
        label={t("cv.profile.identity.name")}
        value={identity.name}
        required
        onChange={(name) => set({ name })}
      />
      {OPTIONAL.map((key) => (
        <Field
          key={key}
          path={`identity.${key}`}
          label={t(`cv.profile.identity.${key}`)}
          value={identity[key] ?? ""}
          onChange={(value) => set({ [key]: value || null })}
        />
      ))}
    </Section>
  );
}
