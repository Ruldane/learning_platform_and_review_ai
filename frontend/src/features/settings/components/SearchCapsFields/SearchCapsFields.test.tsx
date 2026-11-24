import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SearchCapsFields } from "./SearchCapsFields";

const QUERIES = "Queries per session";
const PAGES = "Pages read per session";

describe("SearchCapsFields", () => {
  it("affiche les valeurs et les bornes", () => {
    render(<SearchCapsFields maxQueries={12} maxPages={30} onChange={vi.fn()} />);
    const queries = screen.getByLabelText(QUERIES);
    expect(queries).toHaveValue(12);
    expect(queries).toHaveAttribute("min", "1");
    expect(queries).toHaveAttribute("max", "50");
    const pages = screen.getByLabelText(PAGES);
    expect(pages).toHaveValue(30);
    expect(pages).toHaveAttribute("max", "100");
  });

  it("transmet une valeur valide avec l'autre champ inchangé", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchCapsFields maxQueries={12} maxPages={30} onChange={onChange} />);
    const pages = screen.getByLabelText(PAGES);
    await user.clear(pages);
    await user.type(pages, "45");
    expect(onChange).toHaveBeenLastCalledWith({ maxQueries: 12, maxPages: 45 });
  });

  it.each([
    [QUERIES, "51", "Between 1 and 50."],
    [QUERIES, "0", "Between 1 and 50."],
    [PAGES, "101", "Between 1 and 100."],
    [PAGES, "2.5", "Between 1 and 100."],
  ])("refuse %s = %s sans rien transmettre", async (label, typed, message) => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchCapsFields maxQueries={12} maxPages={30} onChange={onChange} />);
    const field = screen.getByLabelText(label);
    await user.clear(field);
    await user.click(field);
    await user.paste(typed);
    expect(onChange).not.toHaveBeenCalled();
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent(message);
  });

  it("refuse un champ vidé et revient à la valeur courante en quittant le champ", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchCapsFields maxQueries={12} maxPages={30} onChange={onChange} />);
    const field = screen.getByLabelText(QUERIES);
    await user.clear(field);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await user.tab();
    expect(field).toHaveValue(12);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("signale une saisie invalide au parent, puis sa correction", async () => {
    const user = userEvent.setup();
    const onInvalidChange = vi.fn();
    render(
      <SearchCapsFields
        maxQueries={12}
        maxPages={30}
        onChange={vi.fn()}
        onInvalidChange={onInvalidChange}
      />,
    );
    const field = screen.getByLabelText(QUERIES);
    await user.clear(field);
    expect(onInvalidChange).toHaveBeenLastCalledWith(true);
    await user.type(field, "20");
    expect(onInvalidChange).toHaveBeenLastCalledWith(false);
  });
});
