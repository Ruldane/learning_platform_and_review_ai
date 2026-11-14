import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { PostingListItemView } from "../viewTypes";
import { PostingList } from "./PostingList";

const postings: PostingListItemView[] = [
  { id: "p1", title: "Ingénieure données", company: "Société Fictive", score: 62, status: "ready" },
  { id: "p2", title: null, company: null, score: null, status: "analyzing" },
  { id: "p3", title: null, company: null, score: null, status: "rejected" },
  { id: "p4", title: "Dév back", company: null, score: null, status: "failed" },
];

describe("PostingList", () => {
  it("shows title, company, score and the state of each posting", () => {
    render(
      <MemoryRouter>
        <PostingList postings={postings} hrefOf={(id) => `/carriere/offres/${id}`} />
      </MemoryRouter>,
    );
    const items = within(screen.getByRole("list", { name: "Offres ajoutées" })).getAllByRole(
      "listitem",
    );
    expect(items).toHaveLength(4);
    expect(within(items[0]!).getByRole("link", { name: "Ingénieure données" })).toHaveAttribute(
      "href",
      "/carriere/offres/p1",
    );
    expect(within(items[0]!).getByText("Société Fictive")).toBeInTheDocument();
    expect(within(items[0]!).getByText("Match : 62/100")).toBeInTheDocument();
    expect(within(items[1]!).getByText("Analyse en cours…")).toBeInTheDocument();
    expect(within(items[1]!).getByRole("link", { name: "Offre sans titre" })).toBeInTheDocument();
    expect(within(items[2]!).getByText("Refusée : ce n'est pas une offre")).toBeInTheDocument();
    expect(within(items[3]!).getByText("Analyse interrompue")).toBeInTheDocument();
  });
});
