/** Types de vue des composants du profil maître : indépendants du contrat d'API (D34). */

/** D'où vient un fait : le CV, LinkedIn, la note de January, ou January elle-même. */
export type FactSourceView = "cv" | "linkedin" | "note" | "january";

/** Une ligne de texte du profil (réalisation, détail, titre, résumé), avec son identifiant stable. */
export interface LineView {
  /** Vide pour une ligne ajoutée à la main : l'identifiant est attribué à l'enregistrement. */
  id: string;
  text: string;
  /** Seuls le titre et le résumé portent leurs sources ; elles repartent telles quelles à l'enregistrement. */
  sources?: FactSourceView[];
}

export interface IdentityView {
  name: string;
  email: string | null;
  phone: string | null;
  location: string | null;
  headline: string | null;
}

export interface ExperienceView {
  id: string;
  role: string;
  company: string;
  location: string | null;
  /** « AAAA-MM » ou « AAAA ». */
  start: string | null;
  end: string | null;
  achievements: LineView[];
  sources: FactSourceView[];
}

export interface EducationView {
  id: string;
  degree: string;
  school: string;
  start: string | null;
  end: string | null;
  details: LineView[];
  sources: FactSourceView[];
}

export interface SkillFactView {
  id: string;
  name: string;
  category: string | null;
  sources: FactSourceView[];
}

export interface ProjectView {
  id: string;
  name: string;
  description: string;
  link: string | null;
  achievements: LineView[];
  sources: FactSourceView[];
}

export interface LanguageView {
  id: string;
  name: string;
  level: string | null;
  sources: FactSourceView[];
}

export interface LinkView {
  id: string;
  label: string;
  url: string;
  sources: FactSourceView[];
}

/** Le profil maître : la seule source de faits des CV (miroir de `MasterProfileData`). */
export interface MasterProfileView {
  identity: IdentityView;
  title: LineView | null;
  summary: LineView | null;
  experiences: ExperienceView[];
  education: EducationView[];
  skills: SkillFactView[];
  projects: ProjectView[];
  languages: LanguageView[];
  links: LinkView[];
}

export type ProfileStatusView = "draft" | "validated";

export interface ProfileVersionView {
  version: number;
  status: ProfileStatusView;
  /** `archivist` (lu dans les documents) ou `january` (modifié par elle) ; autre valeur rendue telle quelle. */
  source: string;
  /** Instant ISO de la création. */
  createdAt: string;
}

/** Ce que January fournit pour créer le profil : le CV en PDF, LinkedIn et une note en option. */
export interface ProfileImportView {
  cv: File;
  linkedin?: File;
  note?: string;
}

/** Une erreur d'enregistrement : le message, et le texte à placer sous chaque champ fautif par son chemin. */
export interface ProfileSaveErrorView {
  message: string;
  /** Chemin d'un champ (`experiences.2.role`) → ce qu'il faut corriger ; jamais la valeur saisie. */
  fields: Record<string, string>;
}

export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const MAX_NOTE_CHARS = 4000;

/** Les sections d'un CV ciblé (miroir de `SectionKey`). */
export type CvSectionView =
  "summary" | "experience" | "education" | "skills" | "projects" | "languages" | "links";

export type ModificationStatusView = "proposed" | "to_confirm" | "accepted" | "refused";
export type ModificationActionView = "rewrite" | "add" | "remove" | "move";
export type ModificationTypeView = "keyword" | "clarity" | "impact" | "order" | "length" | "title";

/** Ce qu'on peut décider d'une modification : l'accepter ou la refuser. */
export type DecisionView = "accepted" | "refused";

/** Une décision envoyée au back : résout à `false` quand elle est refusée (l'éditeur reste ouvert). */
export type DecideResult = void | Promise<boolean>;

/** Ce que January joint à sa décision : le texte qu'elle a modifié, et la confirmation d'un fait. */
export interface DecideOptions {
  after?: string;
  confirm?: boolean;
}

/** Un fait du profil maître sur lequel s'appuie une modification (G2, F4). */
export interface FactRefView {
  id: string;
  label: string;
}

/** Une modification proposée par la revue du CV. */
export interface ModificationView {
  id: string;
  ref: string;
  section: CvSectionView;
  action: ModificationActionView;
  type: ModificationTypeView;
  before: string;
  after: string;
  reason: string;
  status: ModificationStatusView;
  /** Pourquoi la modification est « à confirmer » : un chiffre, un outil ou un titre absent du profil. */
  blocks: string[];
  /** Le slug de l'agent qui l'a proposée (`agentIdentity`). */
  author: string;
  facts: FactRefView[];
  /** Le numéro de la version générée où cette modification acceptée n'a pas pu être placée. */
  ignoredIn?: number | null;
}

export const MAX_EDIT_CHARS = 600;

/**
 * Un écart de mise en page entre l'original et le modèle recréé : la part d'encre (de 0 à 1) de
 * chaque côté, dans une zone de la page.
 */
export interface ZoneView {
  zone: "haut" | "milieu" | "bas" | "gauche" | "droite";
  original: number;
  render: number;
}

export type AtsCheckIdView =
  "selectable_text" | "reading_order" | "standard_headings" | "contact_in_body" | "font_sizes";

export interface AtsCheckView {
  id: AtsCheckIdView;
  passed: boolean;
  /** Une phrase en français, sans donnée du CV. */
  detail: string;
}

/** Les deux indicateurs d'un CV : couverture des exigences et lisibilité machine. */
export interface IndicatorsView {
  coveragePercent: number;
  covered: number;
  total: number;
  /** Les exigences obligatoires que le CV ne couvre pas. */
  missing: string[];
  checks: AtsCheckView[];
}

export type VersionStatusView = "rendering" | "ready" | "pages_exceeded" | "failed";

export interface VersionView {
  id: string;
  number: number;
  status: VersionStatusView;
  pageCount: number | null;
  originalPageCount: number;
  filename: string;
  /** Instant ISO de la création. */
  createdAt: string;
  failureReason: string | null;
}

/** Le rapport de la revue : ce qui joue pour et contre ce CV face à cette offre. */
export interface ReportView {
  /** Le logiciel de recrutement reconnu (« Greenhouse »), ou `null`. */
  ats: string | null;
  atsNotes: string[];
  companySummary: string | null;
  strengths: string[];
  risks: string[];
  eliminatory: string[];
}
