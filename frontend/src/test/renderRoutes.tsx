import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { createQueryWrapper } from "./queryWrapper";

/** Monte des routes en mémoire à `initial`, avec TanStack Query ; renvoie le routeur et un `userEvent`. */
export function renderRoutes(routes: { path: string; element: ReactElement }[], initial: string) {
  const router = createMemoryRouter(routes, { initialEntries: [initial] });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { router, user: userEvent.setup() };
}
