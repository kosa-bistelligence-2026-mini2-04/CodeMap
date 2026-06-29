import type { DocFolderSummary, DocFileSummaryItem } from "@/common/types/contracts";

function findNearestFolder(
    filePath: string,
    folderSummaries: DocFolderSummary[]
): DocFolderSummary | null {
    const dir = filePath.includes("/")
        ? filePath.substring(0, filePath.lastIndexOf("/"))
        : "";
    const sorted = [...folderSummaries].sort(
        (a, b) => b.path.length - a.path.length
    );
    for (const folder of sorted) {
        if (dir === folder.path || dir.startsWith(folder.path + "/")) {
            return folder;
        }
    }
    return null;
}

export function buildFileSummaries(
    readingOrder: string[],
    dangerFiles: string[],
    folderSummaries: DocFolderSummary[]
): DocFileSummaryItem[] {
    const dangerSet = new Set(dangerFiles);
    const priorityMap = new Map<string, number>();
    readingOrder.forEach((p, i) => priorityMap.set(p, i + 1));

    const allPaths = Array.from(new Set([...readingOrder, ...dangerFiles]));

    return allPaths.map((path) => {
        const folder = findNearestFolder(path, folderSummaries);
        const parts = path.split("/");
        return {
            path,
            fileName: parts[parts.length - 1] ?? path,
            priority: priorityMap.get(path) ?? null,
            isDanger: dangerSet.has(path),
            folderPath: folder?.path ?? null,
            folderSummary: folder?.summary ?? null,
        };
    });
}
