import { t } from "@/shared/i18n/t";
import { ProjectBranch, type BranchProps, type TreeEntry } from "./ProjectBranch";

function buildTree(paths: string[]): Map<string, TreeEntry> {
  const root = new Map<string, TreeEntry>();
  for (const path of paths.toSorted()) {
    const parts = path.split("/");
    let parent = root;
    for (const [index, name] of parts.entries()) {
      const entry = parent.get(name) ?? {
        path: parts.slice(0, index + 1).join("/"),
        children: new Map(),
      };
      parent.set(name, entry);
      parent = entry.children;
    }
  }
  return root;
}

export function ProjectTree(props: Omit<BranchProps, "nodes"> & { paths: string[] }) {
  const { paths, ...branch } = props;
  return (
    <nav aria-label={t("ide.project.files")}>
      <ProjectBranch nodes={buildTree(paths)} {...branch} />
    </nav>
  );
}
