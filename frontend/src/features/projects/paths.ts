/** The app addresses that the Portfolio and a project page know about. */
export const PORTFOLIO_PATH = "/skills/portfolio";
/** The skills map (the `skills` manifest: `competences`). */
export const SKILLS_MAP_PATH = "/skills";
/** The master profile (the `cv` manifest: `career/profile`). */
export const PROFILE_PATH = "/career/profile";

/** The address of a project page. */
export const projectPath = (projectId: string) => `${PORTFOLIO_PATH}/${projectId}`;
