/** Les adresses de l'application que le Portfolio et la page d'un projet connaissent. */
export const PORTFOLIO_PATH = "/skills/portfolio";
/** La carte des compétences (le manifeste de `skills` : `competences`). */
export const SKILLS_MAP_PATH = "/skills";
/** Le profil maître (le manifeste de `cv` : `career/profile`). */
export const PROFILE_PATH = "/career/profile";

/** L'adresse de la page d'un projet. */
export const projectPath = (projectId: string) => `${PORTFOLIO_PATH}/${projectId}`;
