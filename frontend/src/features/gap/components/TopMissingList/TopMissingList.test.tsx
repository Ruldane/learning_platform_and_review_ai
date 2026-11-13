import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TopMissingList } from "./TopMissingList";

describe("TopMissingList", () => {
  it("writes each line and opens the skill", async () => {
    const onOpenSkill = vi.fn();
    render(
      <TopMissingList
        items={[
          { skill: "Python", postings: 5, requiredIn: 4 },
          { skill: "Docker", postings: 1, requiredIn: 1 },
          { skill: "Kafka", postings: 2, requiredIn: 0 },
        ]}
        onOpenSkill={onOpenSkill}
      />,
    );
    expect(screen.getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Python — 5 offres, exigée dans 4",
      "Docker — 1 offre, exigée dans 1",
      "Kafka — 2 offres, jamais exigée",
    ]);
    await userEvent.click(screen.getByRole("button", { name: /Python/ }));
    expect(onOpenSkill).toHaveBeenCalledExactlyOnceWith("Python");
  });

  it("says when nothing is missing", () => {
    render(<TopMissingList items={[]} onOpenSkill={vi.fn()} />);
    expect(screen.getByText("Aucune compétence manquante pour l'instant.")).toBeInTheDocument();
  });
});
