import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { DraftView, ProfileText } from "../../api";
import { CopyDraft } from "./CopyDraft";
import { DraftFields, type EditValues } from "./DraftFields";

export function DraftEditor({ draft, text, busy, onSave }: {
  draft: DraftView;
  text: ProfileText;
  busy: boolean;
  onSave: (text: ProfileText) => void;
}) {
  const original = { headline: text.headline, about: text.about, skills: (text.skills ?? []).join("\n") };
  const [values, setValues] = useState<EditValues>(original);
  const dirty = values.headline !== original.headline || values.about !== original.about
    || values.skills !== original.skills;
  const claims = draft.claims ?? [];
  const canCopy = !dirty && !busy && claims.length === 0;
  function save() {
    const skills = [...new Set(values.skills.split("\n").map((skill) => skill.trim()).filter(Boolean))];
    if (!busy) onSave({ headline: values.headline, about: values.about, skills });
  }
  return (
    <form className="grid gap-4" onSubmit={(event) => { event.preventDefault(); save(); }}>
      <DraftFields values={values} onChange={(field, value) => setValues((old) => ({ ...old, [field]: value }))} />
      {claims.length ? (
        <section className="grid gap-2 rounded-md border p-3" aria-label={t("linkedInDrafts.claims")}>
          <h2 className="font-semibold">{t("linkedInDrafts.claims")}</h2>
          <ul>
            {claims.map(({ field, term }, index) => (
              <li key={field + index}>{t(`linkedInDrafts.${field}`)} · {term}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <div className="flex flex-wrap items-start gap-2">
        <Button type="submit" aria-disabled={busy}>{t("linkedInDrafts.check")}</Button>
        <CopyDraft allowed={canCopy} label={t("linkedInDrafts.copyHeadline")} text={values.headline} />
        <CopyDraft allowed={canCopy} label={t("linkedInDrafts.copyAbout")} text={values.about} />
        <CopyDraft allowed={canCopy} label={t("linkedInDrafts.copySkills")} text={values.skills} />
      </div>
    </form>
  );
}
