/** Les adresses de l'application que le Portfolio et la page d'un projet connaissent. */
export const PORTFOLIO_PATH = "/competences/portfolio";
/** La carte des compétences (le manifeste de `skills` : `competences`). */
export const SKILLS_MAP_PATH = "/competences";
/** Le profil maître (le manifeste de `cv` : `carriere/profil`). */
export const PROFILE_PATH = "/carriere/profil";

/** L'adresse de la page d'un projet. */
export const projectPath = (projectId: string) => `${PORTFOLIO_PATH}/${projectId}`;
