import { setupServer } from "msw/node";

/** Shared MSW server: each test adds its handlers with `server.use(...)`. */
export const server = setupServer();
