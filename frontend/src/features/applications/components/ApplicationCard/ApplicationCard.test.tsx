import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeApplication } from "../fixtures";
import { ApplicationCard } from "./ApplicationCard";

describe("ApplicationCard", () => {
  it("shows the company, the position, the application date, the next action and the due reminders", () => {
    render(
      <ApplicationCard
        application={makeApplication({
          company: "Acme",
          title: "Data engineer",
          status: "applied",
          appliedOn: "2026-11-03",
          nextAction: "Relancer",
          nextActionOn: "2026-11-20",
          dueReminders: 2,
        })}
      />,
    );
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("Data engineer")).toBeInTheDocument();
    expect(screen.getByText("Postulée le 03/11/2026")).toBeInTheDocument();
    expect(screen.getByText("Prochaine action : Relancer (20/11/2026)")).toBeInTheDocument();
    expect(screen.getByText("2 relances dues")).toBeInTheDocument();
  });

  it("says when the application is not sent yet and hides the due reminders when there is none", () => {
    render(<ApplicationCard application={makeApplication({ company: "Beta" })} />);
    expect(screen.getByText("Pas encore postulée")).toBeInTheDocument();
    expect(screen.queryByText(/relance/)).toBeNull();
  });

  it("uses the singular for one due reminder", () => {
    render(<ApplicationCard application={makeApplication({ dueReminders: 1 })} />);
    expect(screen.getByText("1 relance due")).toBeInTheDocument();
  });

  it("opens the application from its name, with the company and position as the accessible name", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(
      <ApplicationCard
        application={makeApplication({ id: "x", company: "Acme", title: "Data engineer" })}
        onOpen={onOpen}
      />,
    );
    await user.click(
      screen.getByRole("button", { name: "Ouvrir la fiche de Acme, poste Data engineer" }),
    );
    expect(onOpen).toHaveBeenCalledWith("x");
  });

  it("shows the status badge only when asked to", () => {
    const application = makeApplication({ status: "offer" });
    const { rerender } = render(<ApplicationCard application={application} />);
    expect(screen.queryByText("Offre")).toBeNull();
    rerender(<ApplicationCard application={application} showStatus />);
    expect(screen.getByText("Offre")).toBeInTheDocument();
  });
});
