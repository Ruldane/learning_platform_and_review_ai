import { AccountMenu } from "./components/AccountMenu";
import { useLogout } from "./hooks/useLogout";
import { useMe } from "./hooks/useMe";

/** L'emplacement `topbar` de la feature : le compte connecté, en mode Google seulement. */
export function AccountMenuSlot() {
  const me = useMe();
  const logout = useLogout();
  if (me.data?.auth_mode !== "google") return null;
  return (
    <AccountMenu
      email={me.data.email ?? me.data.name ?? ""}
      onLogout={() => logout.mutate()}
      pending={logout.isPending}
      failed={logout.isError}
    />
  );
}
