import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router";
import { t } from "@/shared/i18n/t";
import { HomePage } from "../pages/HomePage";
import { NotFoundPage } from "../pages/NotFoundPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

/** Coquille de l'application : fournisseurs, lien d'évitement, routes. */
export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <a
          href="#contenu"
          className="sr-only focus:not-sr-only focus:absolute focus:m-2 focus:rounded-md focus:bg-card focus:px-3 focus:py-2"
        >
          {t("app.skipToContent")}
        </a>
        <main id="contenu" className="mx-auto max-w-3xl px-4 py-10">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
