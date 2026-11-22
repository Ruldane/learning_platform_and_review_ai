import { t } from "@/shared/i18n/t";
import type { Design } from "../../systemDesignApi";

export function SystemDesignSubject({ subject }: { subject: Design["subject"] }) {
  return (
    <section className="flex max-w-3xl flex-col gap-2">
      <h2 className="text-xl font-semibold">{subject.title}</h2>
      <p>{subject.situation}</p>
      <ul aria-label={t("systemDesign.requirements")} className="list-disc space-y-1 pl-6">
        {subject.requirements.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
