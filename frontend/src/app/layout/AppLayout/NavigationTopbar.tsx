import { useLabPreferences } from "@/features/lab/hooks/useLabPreferences";
import type { NavGroup } from "../../buildNav";
import { pinnedDestinations, type Destination } from "../../navigation";
import { Topbar } from "../Topbar";
import { TopNav } from "../TopNav";

export function NavigationTopbar({ bare, groups, cards }: {
  bare: boolean; groups: NavGroup[]; cards: Destination[];
}) {
  const { preferences } = useLabPreferences(!bare);
  const pins = pinnedDestinations(cards, preferences.data?.pinned ?? []);
  return <Topbar menus={bare ? null : <TopNav groups={groups} pins={pins} />} />;
}
