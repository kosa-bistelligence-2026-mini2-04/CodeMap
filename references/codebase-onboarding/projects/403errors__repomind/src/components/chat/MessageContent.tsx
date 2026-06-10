import { memo, useMemo, useCallback, type HTMLAttributes, type ReactNode } from "react";

import { EnhancedMarkdown } from "@/components/EnhancedMarkdown";
import { Mermaid } from "@/components/Mermaid";
import { CodeBlock } from "@/components/CodeBlock";
import { compileMermaidFromJSON } from "@/lib/diagram-utils";
import { repairMarkdown } from "@/lib/markdown-utils";
import { Loader2, ArrowUpRight } from "lucide-react";
import { FolderIcon } from "@/components/FileIcon";

interface MessageIdentity {
    id: string;
}

interface MessageContentProps {
    content: string;
    messageId: string;
    messages?: MessageIdentity[];
    currentOwner?: string;
    currentRepo?: string;
    isStreaming?: boolean;
    fileTree?: { path: string }[];
}

interface MarkdownCodeProps extends HTMLAttributes<HTMLElement> {
    className?: string;
    children?: ReactNode;
    inline?: boolean;
}

interface MarkdownContainerProps {
    children?: ReactNode;
}

function stripEliteSvgBanner(content: string): string {
    return content
        .replace(
            /(?:^|\n)\s*Applying Elite SVG 2\.0 System:\s*\[✓\]\s*Smooth SMIL Splines\s*\[✓\]\s*Precise Bead Math\s*\[✓\]\s*Premium Defs Applied\.?\s*(?:\n|$)/gi,
            "\n"
        )
        .trimStart();
}

function MessageContentBase({
    content,
    currentOwner,
    currentRepo,
    isStreaming = false,
    fileTree = [],
}: MessageContentProps) {
    const repairedContent = useMemo(
        () => repairMarkdown(stripEliteSvgBanner(content)),
        [content]
    );
    const isStreamingMessage = isStreaming;

    const resolvePath = useCallback((path: string, isFolder: boolean) => {
        if (!fileTree || fileTree.length === 0) return path;
        
        // Exact match
        if (fileTree.some(f => f.path === path)) return path;
        
        // Find all matches that end with the given path
        const matches = fileTree.filter(f => f.path.endsWith('/' + path) || f.path === path);
        if (matches.length === 1) return matches[0].path;
        
        if (matches.length > 1) {
            // Priority 1: src or lib
            const priorityMatch = matches.find(m => m.path.startsWith('src/') || m.path.startsWith('lib/'));
            if (priorityMatch) return priorityMatch.path;
            
            // Priority 2: Not tests
            const nonTestMatch = matches.find(m => !m.path.includes('test'));
            if (nonTestMatch) return nonTestMatch.path;
            
            // Priority 3: Shortest path
            return matches.sort((a, b) => a.path.length - b.path.length)[0].path;
        }

        // For folders, we can also check if any file starts with that path
        if (isFolder) {
            const prefixMatch = fileTree.find(f => f.path.startsWith(path + '/'));
            if (prefixMatch) return path; // Folder exists as a prefix
        }

        return path;
    }, [fileTree]);

    const components = {
        code: ({ className, children, inline, ...props }: MarkdownCodeProps) => {
            const match = /language-([\w-]+)/.exec(className ?? "");
            const language = (match?.[1] ?? "").toLowerCase();
            const isMermaid = language === "mermaid";
            const isMermaidJson = language === "mermaid-json";
            const isJsonLanguage = language === "json";
            const rawContent = String(children ?? "").replace(/\n$/, "");
            const trimmedContent = rawContent.trim();
            const looksLikeMermaidJsonPayload =
                trimmedContent.startsWith("{") &&
                (
                    /"diagramType"\s*:\s*"/.test(trimmedContent) ||
                    (/"nodes"\s*:/.test(trimmedContent) && /"edges"\s*:/.test(trimmedContent)) ||
                    (/"participants"\s*:/.test(trimmedContent) && /"messages"\s*:/.test(trimmedContent))
                );

            if (isMermaid) {
                return (
                    <Mermaid
                        chart={rawContent}
                        isStreaming={isStreamingMessage}
                    />
                );
            }

            if (language === "svg") {
                return (
                    <div className="my-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                        <p className="mb-2 text-xs text-amber-200">
                            Direct SVG rendering is deprecated. Showing legacy SVG source.
                        </p>
                        <CodeBlock
                            language="svg"
                            value={rawContent}
                            components={components}
                            owner={currentOwner}
                            repo={currentRepo}
                        />
                    </div>
                );
            }

            if (isMermaidJson || isJsonLanguage || looksLikeMermaidJsonPayload) {
                const jsonContent = rawContent;
                try {
                    const compiled = compileMermaidFromJSON(JSON.parse(jsonContent));
                    if (compiled.valid && compiled.mermaid) {
                        return <Mermaid chart={compiled.mermaid} isStreaming={isStreamingMessage} />;
                    }
                    if (!compiled.valid && isMermaidJson) {
                        console.warn('[mermaid-json] Compile failed:', compiled.error, '\nRaw JSON:', jsonContent);
                    }
                } catch (e) {
                    if (isMermaidJson) {
                        console.warn('[mermaid-json] JSON parse error:', e, '\nRaw content:', jsonContent);
                    }
                }

                if (isStreamingMessage && (isMermaidJson || isJsonLanguage || looksLikeMermaidJsonPayload)) {
                    return (
                        <div className="flex items-center gap-2 p-4 bg-zinc-900/50 rounded-lg border border-white/10">
                            <Loader2 className="w-4 h-4 animate-spin text-zinc-400" />
                            <span className="text-zinc-400 text-sm">Generating diagram...</span>
                        </div>
                    );
                }

                return (
                    <CodeBlock
                        language="json"
                        value={jsonContent}
                        components={components}
                        owner={currentOwner}
                        repo={currentRepo}
                    />
                );
            }

            const childrenStr = rawContent;
            const isBlock = childrenStr.endsWith("\n");
            const shouldRenderBlock = Boolean(match) || isBlock || inline === false;

            if (shouldRenderBlock) {
                return (
                    <CodeBlock
                        language={match?.[1] ?? "markdown"}
                        value={childrenStr}
                        components={components}
                        owner={currentOwner}
                        repo={currentRepo}
                    />
                );
            }

            // Detect if this is likely a file or folder path
            const hasExtension = /\.(ts|tsx|js|jsx|py|md|css|json|yaml|yml|sh|html|go|rs|java|c|cpp|h|sql|env|toml)$/.test(childrenStr);
            const hasSlash = childrenStr.includes('/');
            const isKnownFolder = ['src', 'lib', 'app', 'components', 'pages', 'public', 'tests', 'docs'].includes(childrenStr.toLowerCase());

            const isFilePath = !match && hasExtension && !childrenStr.includes(' ') && childrenStr.length > 2;
            const isFolder = !match && !isFilePath && (
                childrenStr.endsWith('/') || 
                (hasSlash && !childrenStr.includes(' ')) ||
                isKnownFolder
            ) && childrenStr.length > 2;

            if (isFilePath) {
                const fullPath = resolvePath(childrenStr, false);
                const exists = fileTree.length > 0 && fileTree.some(f => f.path === fullPath);

                if (exists) {
                    return (
                        <button
                            onClick={(e) => {
                                e.preventDefault();
                                window.dispatchEvent(new CustomEvent('open-file-preview', { detail: fullPath }));
                            }}
                            className="inline-flex items-baseline gap-1 underline decoration-dashed decoration-zinc-500/50 underline-offset-[3px] hover:decoration-zinc-400 text-sm font-mono text-zinc-300 hover:text-zinc-100 transition-all cursor-pointer group"
                            title={`Open ${fullPath}`}
                        >
                            <ArrowUpRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-400 transition-colors" />
                            {children}
                        </button>
                    );
                }
            }

            if (isFolder) {
                const baseFolder = childrenStr.endsWith('/') ? childrenStr.slice(0, -1) : childrenStr;
                const fullFolderPath = resolvePath(baseFolder, true);
                const exists = fileTree.length > 0 && (
                    fileTree.some(f => f.path === fullFolderPath) || 
                    fileTree.some(f => f.path.startsWith(fullFolderPath + '/'))
                );

                if (exists) {
                    return (
                        <button
                            onClick={(e) => {
                                e.preventDefault();
                                window.dispatchEvent(new CustomEvent('reveal-folder', { detail: fullFolderPath }));
                            }}
                            className="inline-flex items-baseline gap-1 underline decoration-dashed decoration-zinc-500/50 underline-offset-[3px] hover:decoration-zinc-400 text-sm font-mono text-zinc-300 hover:text-zinc-100 transition-all cursor-pointer group"
                            title={`Reveal ${fullFolderPath}`}
                        >
                            <FolderIcon name={childrenStr} isExpanded={false} className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-400 transition-colors" />
                            {children}
                        </button>
                    );
                }
            }

            return (
                <code
                    className="bg-zinc-800/30 px-1.5 py-0.5 rounded border border-white/5 text-zinc-300 font-mono text-sm"
                    {...props}
                >
                    {children}
                </code>
            );
        },
        p: ({ children }: MarkdownContainerProps) => (
            <p className="mb-4 leading-relaxed last:mb-0">{children}</p>
        ),
        pre: ({ children }: MarkdownContainerProps) => <>{children}</>,
        table: ({ children }: MarkdownContainerProps) => (
            <div className="overflow-x-auto my-4">
                <table className="min-w-full border-collapse border border-zinc-700">{children}</table>
            </div>
        ),
        thead: ({ children }: MarkdownContainerProps) => (
            <thead className="bg-zinc-800">{children}</thead>
        ),
        tbody: ({ children }: MarkdownContainerProps) => (
            <tbody className="bg-zinc-900/50">{children}</tbody>
        ),
        tr: ({ children }: MarkdownContainerProps) => (
            <tr className="border-b border-zinc-700">{children}</tr>
        ),
        th: ({ children }: MarkdownContainerProps) => (
            <th className="px-4 py-2 text-left text-sm font-semibold text-white border border-zinc-700">
                {children}
            </th>
        ),
        td: ({ children }: MarkdownContainerProps) => (
            <td className="px-4 py-2 text-sm text-zinc-300 border border-zinc-700">{children}</td>
        ),
    };

    return (
        <div className="w-full [&>*:first-child]:!mt-0">
            <EnhancedMarkdown
                content={repairedContent}
                components={components}
                currentOwner={currentOwner}
                currentRepo={currentRepo}
                isStreaming={isStreaming}
                fileTree={fileTree}
            />
        </div>
    );
}

export const MessageContent = memo(MessageContentBase, (prev, next) => (
    prev.content === next.content &&
    prev.messageId === next.messageId &&
    prev.currentOwner === next.currentOwner &&
    prev.currentRepo === next.currentRepo &&
    prev.isStreaming === next.isStreaming &&
    prev.fileTree === next.fileTree
));
