import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider, type Location, type RouteObject } from "react-router";
import { createQueryWrapper } from "./queryWrapper";

/** Mounts in-memory routes at `initial` with TanStack Query; returns the router and `userEvent`. */
export function renderRoutes(routes: RouteObject[], initial: string | Partial<Location>) {
  const router = createMemoryRouter(routes, { initialEntries: [initial] });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { router, user: userEvent.setup() };
}
