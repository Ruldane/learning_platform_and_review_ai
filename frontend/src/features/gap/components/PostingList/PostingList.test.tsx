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
        <PostingList postings={postings} hrefOf={(id) => `/career/postings/${id}`} />
      </MemoryRouter>,
    );
    const items = within(screen.getByRole("list", { name: "Added postings" })).getAllByRole(
      "listitem",
    );
    expect(items).toHaveLength(4);
    expect(within(items[0]!).getByRole("link", { name: "Ingénieure données" })).toHaveAttribute(
      "href",
      "/career/postings/p1",
    );
    expect(within(items[0]!).getByText("Société Fictive")).toBeInTheDocument();
    expect(within(items[0]!).getByText("Match: 62/100")).toBeInTheDocument();
    expect(within(items[1]!).getByText("Analyzing…")).toBeInTheDocument();
    expect(within(items[1]!).getByRole("link", { name: "Untitled posting" })).toBeInTheDocument();
    expect(within(items[2]!).getByText("Rejected: this isn't a job posting")).toBeInTheDocument();
    expect(within(items[3]!).getByText("Analysis interrupted")).toBeInTheDocument();
  });
});
