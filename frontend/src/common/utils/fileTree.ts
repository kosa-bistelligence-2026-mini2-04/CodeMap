import type { WorkspaceFile } from "@/common/types/contracts";

export interface FileTreeNode {
  name: string;
  path: string;
  type: "directory" | "file";
  children: FileTreeNode[];
  file?: WorkspaceFile;
}

interface MutableTreeNode extends FileTreeNode {
  children: MutableTreeNode[];
}

export function normalizeRepositoryPath(path: string): string {
  return path.replaceAll("\\", "/").split("/").filter(Boolean).join("/");
}

function compareNodes(left: FileTreeNode, right: FileTreeNode): number {
  if (left.type !== right.type) return left.type === "directory" ? -1 : 1;
  return left.name.localeCompare(right.name, undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

function sortTree(nodes: MutableTreeNode[]): FileTreeNode[] {
  return nodes
    .sort(compareNodes)
    .map((node) => ({
      ...node,
      children: sortTree(node.children),
    }));
}

export function buildFileTree(files: WorkspaceFile[]): FileTreeNode[] {
  const root: MutableTreeNode[] = [];
  const directories = new Map<string, MutableTreeNode>();
  const seenFiles = new Set<string>();

  for (const file of files) {
    const normalizedPath = normalizeRepositoryPath(file.path);
    const segments = normalizedPath.split("/").filter(Boolean);

    if (segments.length === 0) continue;

    let children = root;
    let currentPath = "";

    for (const segment of segments.slice(0, -1)) {
      currentPath = currentPath ? `${currentPath}/${segment}` : segment;
      let directory = directories.get(currentPath);

      if (!directory) {
        directory = {
          name: segment,
          path: currentPath,
          type: "directory",
          children: [],
        };
        directories.set(currentPath, directory);
        children.push(directory);
      }

      children = directory.children;
    }

    if (seenFiles.has(normalizedPath)) continue;

    seenFiles.add(normalizedPath);
    children.push({
      name: segments.at(-1) ?? file.name,
      path: normalizedPath,
      type: "file",
      children: [],
      file: { ...file, path: normalizedPath },
    });
  }

  return sortTree(root);
}

export function getAncestorPaths(path: string): string[] {
  const segments = normalizeRepositoryPath(path).split("/").filter(Boolean);
  return segments.slice(0, -1).map((_, index) => segments.slice(0, index + 1).join("/"));
}
