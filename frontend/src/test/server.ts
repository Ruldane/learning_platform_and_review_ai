import { setupServer } from "msw/node";

/** Serveur MSW partagé : chaque test ajoute ses handlers avec `server.use(...)`. */
export const server = setupServer();
