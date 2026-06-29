import type {
    DocFolderSummary,
    DocReadingOrderItem,
    DocDangerFileItem,
    DocFileSummaryItem,
    DocFileSummaryRaw,
} from "@/common/types/contracts";


export function buildFileSummaries(
    readingOrder: DocReadingOrderItem[],
    dangerFiles: DocDangerFileItem[],
    folderSummaries: DocFolderSummary[],
    fileSummaries: DocFileSummaryRaw[] = []
): DocFileSummaryItem[] {
    const dangerMap = new Map<string, string>(
        dangerFiles.map((d) => [d.path, d.reason])
    );
    const priorityMap = new Map<string, number>(
        readingOrder.map((r) => [r.path, r.rank])
    );
    const fileSummaryMap = new Map<string, string | null>(
        fileSummaries.map((f) => [f.path, f.summary])
    );
    const folderMap = new Map<string, DocFolderSummary>(
        folderSummaries.map((f) => [f.path, f])
    );

    function findNearestFolder(filePath: string): DocFolderSummary | null {
        let dir = filePath.includes("/")
            ? filePath.substring(0, filePath.lastIndexOf("/"))
            : "";
        while (dir.length > 0) {
            if (folderMap.has(dir)) return folderMap.get(dir)!;
            if (!dir.includes("/")) break;
            dir = dir.substring(0, dir.lastIndexOf("/"));
        }
        return folderMap.has("") ? folderMap.get("")! : null;
    }

    const allPaths = Array.from(
        new Set([
            ...readingOrder.map((r) => r.path),
            ...dangerFiles.map((d) => d.path),
            ...fileSummaries.map((f) => f.path),
        ])
    );

    return allPaths.map((path) => {
        const folder = findNearestFolder(path);
        const parts = path.split("/");
        return {
            path,
            fileName: parts[parts.length - 1] ?? path,
            priority: priorityMap.get(path) ?? null,
            isDanger: dangerMap.has(path),
            dangerReason: dangerMap.get(path) ?? null,
            folderPath: folder?.path ?? null,
            folderSummary: folder?.summary ?? null,
            summary: fileSummaryMap.get(path) ?? null,
        };
    });
}
