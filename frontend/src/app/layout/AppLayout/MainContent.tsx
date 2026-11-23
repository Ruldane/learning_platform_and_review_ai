import { useEffect, useRef } from "react";
import { Outlet, useLocation, useMatches } from "react-router";
import { t, type MessageKey } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";

export function MainContent({ wide }: { wide: boolean }) {
  const { pathname } = useLocation();
  const previous = useRef(pathname);
  const main = useRef<HTMLElement>(null);
  const matches = useMatches();
  const description = (matches.at(-1)?.handle as { description?: MessageKey } | undefined)?.description;
  useEffect(() => {
    if (previous.current === pathname) return;
    previous.current = pathname;
    if (!main.current?.contains(document.activeElement)) main.current?.focus();
  }, [pathname]);
  return (
    <main ref={main} id="contenu" tabIndex={-1} aria-describedby={description ? "description-page" : undefined}
      className={cn("mx-auto w-full min-w-0 flex-1 px-6 py-8 focus:outline-none",
        wide ? "max-w-7xl" : "max-w-4xl")}>
      {description ? <p id="description-page" className="mb-4 text-sm text-muted-foreground">{t(description)}</p> : null}
      <Outlet />
    </main>
  );
}
