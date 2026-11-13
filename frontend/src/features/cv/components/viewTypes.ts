/** Types de vue des composants du profil maître : indépendants du contrat d'API (D34). */

/** D'où vient un fait : le CV, LinkedIn, la note de January, ou January elle-même. */
export type FactSourceView = "cv" | "linkedin" | "note" | "january";

/** Une ligne de texte du profil (réalisation, détail, titre, résumé), avec son identifiant stable. */
export interface LineView {
  /** Vide pour une ligne ajoutée à la main : l'identifiant est attribué à l'enregistrement. */
  id: string;
  text: string;
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
