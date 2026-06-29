import type {
    DocFolderSummary,
    DocReadingOrderItem,
    DocDangerFileItem,
    DocFileSummaryItem,
} from "@/common/types/contracts";

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
    readingOrder: DocReadingOrderItem[],
    dangerFiles: DocDangerFileItem[],
    folderSummaries: DocFolderSummary[]
): DocFileSummaryItem[] {
    const dangerMap = new Map<string, string>(
        dangerFiles.map((d) => [d.path, d.reason])
    );
    const priorityMap = new Map<string, number>(
        readingOrder.map((r) => [r.path, r.rank])
    );

    const allPaths = Array.from(
        new Set([
            ...readingOrder.map((r) => r.path),
            ...dangerFiles.map((d) => d.path),
        ])
    );

    return allPaths.map((path) => {
        const folder = findNearestFolder(path, folderSummaries);
        const parts = path.split("/");
        return {
            path,
            fileName: parts[parts.length - 1] ?? path,
            priority: priorityMap.get(path) ?? null,
            isDanger: dangerMap.has(path),
            dangerReason: dangerMap.get(path) ?? null,
            folderPath: folder?.path ?? null,
            folderSummary: folder?.summary ?? null,
        };
    });
}
