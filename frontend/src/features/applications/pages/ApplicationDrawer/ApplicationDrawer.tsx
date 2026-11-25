import { X } from "lucide-react";
import { Dialog } from "radix-ui";
import { useLocation, useNavigate, useParams } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { useApplication } from "../../hooks/useApplication";
import { openedInfo } from "../../navState";
import { BOARD_PATH } from "../../urls";
import { DrawerBody } from "./DrawerBody";
import { DrawerUnavailable } from "./DrawerUnavailable";

/**
 * La fiche d'une candidature en tiroir (`/applications/:applicationId`), par-dessus le suivi :
 * boîte de dialogue modale (le focus y reste, Échap la ferme et rend le focus à ce qui l'a ouverte).
 * Une fiche inconnue (404) le dit et ramène au suivi.
 */
export function ApplicationDrawer() {
  const { applicationId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const query = useApplication(applicationId);
  const close = () => void navigate(BOARD_PATH);
  const detail = query.data;
  const title = detail ? `${detail.company}, ${detail.title}` : t("applications.drawer.label");

  return (
    <Dialog.Root open onOpenChange={(open) => !open && close()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-foreground/30" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col gap-4 overflow-y-auto border-l bg-background p-6 shadow-xl"
        >
          <header className="flex items-start justify-between gap-3">
            <Dialog.Title className="text-xl font-semibold break-words">{title}</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label={t("applications.drawer.close")}>
                <X aria-hidden="true" />
              </Button>
            </Dialog.Close>
          </header>
          {detail ? (
            <DrawerBody detail={detail} info={openedInfo(location.state)} />
          ) : (
            <DrawerUnavailable
              error={query.isError ? query.error : null}
              onRetry={() => void query.refetch()}
              onBack={close}
            />
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
