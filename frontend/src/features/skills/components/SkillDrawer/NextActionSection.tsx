import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { SkillDetailView } from "../viewTypes";
import { NextActionBlock } from "./NextActionBlock";
import { Section } from "./Section";

export function NextActionSection({ detail }: { detail: SkillDetailView }) {
  return (
    <Section title={t("skills.drawer.nextAction")}>
      <NextActionBlock action={detail.nextAction} />
      {detail.evidence.length > 0 && (
        <Button asChild variant="outline" size="sm">
          <Link to={`/competences/transfert?competence=${encodeURIComponent(detail.id)}`}>
            {t("skillTransfer.drawer")}
          </Link>
        </Button>
      )}
    </Section>
  );
}
