import type {
  DuplicateView,
  GapRowView,
  MissingSkillView,
  PostingAnalysisView,
  PostingListItemView,
} from "./components/viewTypes";
import type { DuplicateAlertView } from "@/shared/ui/DuplicateAlert";
import type {
  ApplicationAlertOut,
  ApplicationCheckOut,
  DuplicateOut,
  GapRowOut,
  PostingAnalysisOut,
  PostingSummaryOut,
  TopMissingOut,
} from "./types";

/** L'analyse du contrat → la fiche de l'offre (mots clés réduits à leur terme, critères à leur texte). */
export function toAnalysisView(analysis: PostingAnalysisOut): PostingAnalysisView {
  return {
    title: analysis.title,
    company: analysis.company,
    level: analysis.level,
    location: analysis.location,
    remote: analysis.remote,
    requirements: analysis.requirements.map(({ text, required }) => ({ text, required })),
    keywords: analysis.keywords.map((keyword) => keyword.term),
    eliminatory: analysis.eliminatory.map((item) => item.text),
    tools: analysis.tools,
  };
}

export function toDuplicateViews(duplicates: DuplicateOut[]): DuplicateView[] {
  return duplicates.map((duplicate) => ({
    level: duplicate.level,
    postingId: duplicate.posting_id,
    title: duplicate.title,
    company: duplicate.company,
    createdAt: duplicate.created_at,
  }));
}

export function toGapRows(rows: GapRowOut[]): GapRowView[] {
  return rows.map((row) => ({
    skill: row.skill,
    required: row.required,
    level: row.level,
    action: row.action,
    week: row.week,
    source: row.source,
  }));
}

export function toMissingViews(items: TopMissingOut[]): MissingSkillView[] {
  return items.map((item) => ({
    skill: item.skill,
    postings: item.postings,
    requiredIn: item.required_in,
  }));
}

export function toPostingListItems(postings: PostingSummaryOut[]): PostingListItemView[] {
  return postings.map(({ id, title, company, score, status }) => ({
    id,
    title,
    company,
    score,
    status,
  }));
}

/** Les doublons certains d'une offre déjà connue (réponse 200 de `POST /postings`). */
export function certainDuplicate(posting: {
  id: string;
  title: string | null;
  company: string | null;
  created_at: string;
}): DuplicateView {
  return {
    level: "certain",
    postingId: posting.id,
    title: posting.title,
    company: posting.company,
    createdAt: posting.created_at,
  };
}

/** Une alerte de candidature du contrat → celle que l'alerte de doublon partagée affiche. */
export function toApplicationAlertView(alert: ApplicationAlertOut): DuplicateAlertView {
  return {
    level: alert.level,
    applicationId: alert.application_id,
    company: alert.company,
    title: alert.title,
    status: alert.status,
    message: alert.message,
  };
}

export function toExistingApplicationView(ref: NonNullable<ApplicationCheckOut["own"]>) {
  return { id: ref.id, company: ref.company, title: ref.title, status: ref.status };
}
