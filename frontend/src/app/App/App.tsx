import { RouterProvider, type DataRouter } from "react-router";
import { Providers } from "../Providers";

/** Racine de l'application : fournisseurs globaux puis routeur (construit par `buildRouter`). */
export function App({ router }: { router: DataRouter }) {
  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}
