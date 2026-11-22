export interface TreeEntry {
  readonly path: string;
  readonly children: Map<string, TreeEntry>;
}

export interface BranchProps {
  nodes: Map<string, TreeEntry>;
  current: string;
  onOpen: (path: string) => void;
}

export function ProjectBranch({ nodes, current, onOpen }: BranchProps) {
  return (
    <ul className="ml-2 border-l border-border pl-2 text-sm">
      {Array.from(nodes, ([name, { path, children }]) => (
        <li key={path}>
          {children.size ? (
            <details open>
              <summary className="cursor-pointer rounded px-1 py-0.5 focus-visible:ring-2 focus-visible:ring-ring">
                {name}
              </summary>
              <ProjectBranch nodes={children} current={current} onOpen={onOpen} />
            </details>
          ) : (
            <button
              type="button"
              aria-label={path}
              aria-current={current === path ? "true" : undefined}
              className="rounded px-1 py-0.5 text-left focus-visible:ring-2 focus-visible:ring-ring aria-current:bg-muted"
              onClick={() => onOpen(path)}
            >
              {name}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
