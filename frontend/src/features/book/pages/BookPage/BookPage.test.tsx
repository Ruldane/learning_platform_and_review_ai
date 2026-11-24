import { screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { BookPage } from "./BookPage";

const PROGRAM = "p-1";
const API = `${apiBaseUrl}/api/v1`;
const BOOK = `${API}/programs/${PROGRAM}/book`;

it("demande une édition et affiche les deux téléchargements quand elle est prête", async () => {
  let status = "not_requested";
  server.use(
    http.get(`${API}/programs`, () => HttpResponse.json([{ id: PROGRAM, title: "Python" }])),
    http.get(BOOK, () =>
      HttpResponse.json({
        status,
        chapters: status === "ready" ? 2 : 0,
        available: status === "ready",
        rendered_at: null,
      }),
    ),
    http.post(BOOK, () => {
      status = "queued";
      return HttpResponse.json(
        { status, chapters: 0, available: false, rendered_at: null },
        {
          status: 202,
        },
      );
    }),
  );
  const { user } = renderRoutes(
    [{ path: "/learn/book/:programId?", element: <BookPage pollMs={20} /> }],
    `/learn/book/${PROGRAM}`,
  );
  await user.click(await screen.findByRole("button", { name: "Prepare the book" }));
  expect(await screen.findByText("The edition is being prepared.")).toBeVisible();
  expect(screen.queryByRole("link", { name: "Download as PDF" })).toBeNull();
  status = "ready";
  expect(await screen.findByRole("link", { name: "Download as PDF" })).toHaveAttribute(
    "href",
    `${BOOK}/pdf`,
  );
  expect(screen.getByRole("link", { name: "Download as EPUB" })).toHaveAttribute(
    "href",
    `${BOOK}/epub`,
  );
  expect(screen.getByRole("link", { name: "Download as PDF" })).toHaveFocus();
  expect(screen.getByText("Chapters published in the edition: 2")).toBeVisible();
});
