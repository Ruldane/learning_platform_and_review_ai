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
    expect(screen.getByText("Applied on 03/11/2026")).toBeInTheDocument();
    expect(screen.getByText("Next action: Relancer (20/11/2026)")).toBeInTheDocument();
    expect(screen.getByText("2 follow-ups due")).toBeInTheDocument();
  });

  it("says when the application is not sent yet and hides the due reminders when there is none", () => {
    render(<ApplicationCard application={makeApplication({ company: "Beta" })} />);
    expect(screen.getByText("Not applied yet")).toBeInTheDocument();
    expect(screen.queryByText(/relance/)).toBeNull();
  });

  it("uses the singular for one due reminder", () => {
    render(<ApplicationCard application={makeApplication({ dueReminders: 1 })} />);
    expect(screen.getByText("1 follow-up due")).toBeInTheDocument();
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
      screen.getByRole("button", { name: "Open the Acme application, Data engineer role" }),
    );
    expect(onOpen).toHaveBeenCalledWith("x");
  });

  it("shows the status badge only when asked to", () => {
    const application = makeApplication({ status: "offer" });
    const { rerender } = render(<ApplicationCard application={application} />);
    expect(screen.queryByText("Offer")).toBeNull();
    rerender(<ApplicationCard application={application} showStatus />);
    expect(screen.getByText("Offer")).toBeInTheDocument();
  });
});
