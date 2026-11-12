import { useEffect, useId, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { SkillDetailView } from "../viewTypes";
import { EvidenceList } from "./EvidenceList";
import { NextActionBlock } from "./NextActionBlock";
import { PostingList } from "./PostingList";
import { Section } from "./Section";
import { SkillSummary } from "./SkillSummary";

interface SkillDrawerProps {
  /** `null` : tiroir fermé. */
  detail: SkillDetailView | null;
  onClose: () => void;
}

/**
 * Détail d'une compétence, à droite de la carte : preuves (avec leurs liens), offres qui l'exigent
 * et prochaine action. Un `role="dialog"` volontairement non modal : la carte derrière reste
 * utilisable. Le focus arrive sur le titre à chaque compétence ouverte, Échap ferme le tiroir.
 */
export function SkillDrawer({ detail, onClose }: SkillDrawerProps) {
  const titleId = useId();
  const titleRef = useRef<HTMLHeadingElement>(null);
  const skillId = detail?.id;

  useEffect(() => {
    if (skillId !== undefined) titleRef.current?.focus();
  }, [skillId]);

  useEffect(() => {
    if (skillId === undefined) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented) onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [skillId, onClose]);

  if (detail === null) return null;
  return (
    <section
      role="dialog"
      aria-labelledby={titleId}
      className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col gap-4 overflow-y-auto border-l border-border bg-card p-5 shadow-lg"
    >
      <header className="flex items-start justify-between gap-3">
        <h2
          id={titleId}
          ref={titleRef}
          tabIndex={-1}
          className="text-lg font-semibold outline-none"
        >
          {detail.name}
        </h2>
        <Button variant="outline" size="sm" onClick={onClose}>
          {t("skills.drawer.close")}
        </Button>
      </header>
      <SkillSummary detail={detail} />
      <Section title={t("skills.drawer.nextAction")}>
        <NextActionBlock action={detail.nextAction} />
      </Section>
      <Section title={t("skills.drawer.evidence")}>
        <EvidenceList evidence={detail.evidence} />
      </Section>
      <Section title={t("skills.drawer.postings")}>
        <PostingList postings={detail.postings} />
      </Section>
    </section>
  );
}
