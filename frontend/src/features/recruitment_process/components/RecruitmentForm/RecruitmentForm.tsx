import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface Choice {
  id: string;
  title: string;
}

interface Props {
  postings: Choice[];
  projects: Choice[];
  busy: boolean;
  onCreate: (posting: string, project: string | null) => void;
}

function choices(items: Choice[]) {
  return items.map(({ id, title }) => <option key={id} value={id}>{title}</option>);
}

export function RecruitmentForm({ postings, projects, busy, onCreate }: Props) {
  const [posting, setPosting] = useState("");
  const [project, setProject] = useState("");
  const offerId = useId();
  const projectId = useId();
  if (postings.length === 0) return <p>{t("recruitmentProcess.noOffer")}</p>;
  return (
    <form className="grid gap-3 rounded-xl border bg-card p-4" onSubmit={(event) => {
      event.preventDefault();
      if (posting) onCreate(posting, project || null);
    }}>
      <label htmlFor={offerId}>{t("recruitmentProcess.offer")}</label>
      <select id={offerId} className={fieldClass} value={posting} onChange={(event) => setPosting(event.target.value)}>
        <option value="">{t("recruitmentProcess.chooseOffer")}</option>
        {choices(postings)}
      </select>
      <label htmlFor={projectId}>{t("recruitmentProcess.optionalProject")}</label>
      <select id={projectId} className={fieldClass} value={project} onChange={(event) => setProject(event.target.value)}>
        <option value="">{t("recruitmentProcess.noProject")}</option>
        {choices(projects)}
      </select>
      <Button type="submit" className="justify-self-start" disabled={!posting || busy}>
        {t("recruitmentProcess.create")}
      </Button>
    </form>
  );
}
