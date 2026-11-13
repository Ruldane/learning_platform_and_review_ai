import type { MasterProfileView } from "../viewTypes";
import { EducationSection } from "./EducationSection";
import { ExperiencesSection } from "./ExperiencesSection";
import { IdentitySection } from "./IdentitySection";
import { LanguagesSection } from "./LanguagesSection";
import { LinksSection } from "./LinksSection";
import { ProjectsSection } from "./ProjectsSection";
import { SkillsSection } from "./SkillsSection";
import { TextLineSection } from "./TextLineSection";

interface ProfileSectionsProps {
  profile: MasterProfileView;
  onChange: (changes: Partial<MasterProfileView>) => void;
}

/** Les neuf sections du profil, dans l'ordre du CV. */
export function ProfileSections({ profile, onChange }: ProfileSectionsProps) {
  return (
    <>
      <IdentitySection
        identity={profile.identity}
        onChange={(identity) => onChange({ identity })}
      />
      <TextLineSection
        kind="title"
        line={profile.title}
        onChange={(title) => onChange({ title })}
      />
      <TextLineSection
        kind="summary"
        line={profile.summary}
        onChange={(summary) => onChange({ summary })}
      />
      <ExperiencesSection
        items={profile.experiences}
        onChange={(experiences) => onChange({ experiences })}
      />
      <EducationSection
        items={profile.education}
        onChange={(education) => onChange({ education })}
      />
      <SkillsSection items={profile.skills} onChange={(skills) => onChange({ skills })} />
      <ProjectsSection items={profile.projects} onChange={(projects) => onChange({ projects })} />
      <LanguagesSection
        items={profile.languages}
        onChange={(languages) => onChange({ languages })}
      />
      <LinksSection items={profile.links} onChange={(links) => onChange({ links })} />
    </>
  );
}
