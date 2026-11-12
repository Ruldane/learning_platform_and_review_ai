import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { GoalRow } from "../viewTypes";
import { GoalList } from "./GoalList";

const goals: GoalRow[] = [
  {
    id: "g2",
    text: "Devenir ingénieure data",
    targetRole: "Data engineer",
    deadline: "2027-06-30",
    weeklyHours: 8,
    status: "planned",
    programId: "pr2",
  },
  {
    id: "g1",
    text: "Apprendre Rust",
    targetRole: null,
    deadline: null,
    weeklyHours: null,
    status: "council",
    programId: null,
  },
];

const renderList = (rows: GoalRow[]) =>
  render(
    <MemoryRouter>
      <GoalList goals={rows} />
    </MemoryRouter>,
  );

describe("GoalList", () => {
  it("lists the goals with their status", () => {
    renderList(goals);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]!).getByText("Devenir ingénieure data")).toBeInTheDocument();
    expect(within(items[0]!).getByText("Programme planifié")).toBeInTheDocument();
    expect(within(items[0]!).getByText("Data engineer")).toBeInTheDocument();
    expect(within(items[0]!).getByText("8 h par semaine")).toBeInTheDocument();
    expect(within(items[1]!).getByText("Le Conseil délibère")).toBeInTheDocument();
  });

  it("links to the council of each goal", () => {
    renderList(goals);
    const links = screen.getAllByRole("link", { name: /Ouvrir le Conseil/ });
    expect(links.map((a) => a.getAttribute("href"))).toEqual([
      "/apprendre/objectifs/g2/conseil",
      "/apprendre/objectifs/g1/conseil",
    ]);
  });

  it("links to the program only once there is a parcours", () => {
    renderList(goals);
    const links = screen.getAllByRole("link", { name: /Voir le programme/ });
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/apprendre/programme/pr2");
  });

  it("links a chosen goal without program id to the program index", () => {
    renderList([{ ...goals[1]!, status: "chosen" }]);
    expect(screen.getByRole("link", { name: /Voir le programme/ })).toHaveAttribute(
      "href",
      "/apprendre/programme",
    );
  });
});
