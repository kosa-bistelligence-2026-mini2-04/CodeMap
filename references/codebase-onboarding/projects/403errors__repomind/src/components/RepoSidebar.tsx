"use client";

import { useState, useEffect } from "react";
import { FileIcon, FolderIcon } from "./FileIcon";
import { GitBranch, ChevronRight, ChevronDown, X, AlertCircle, Star, GitFork, CircleDot, Calendar } from "lucide-react";
import { FileNode, GitHubRepo } from "@/lib/github";
import { cn } from "@/lib/utils";

interface RepoSidebarProps {
    fileTree: FileNode[];
    repoName: string;
    isOpen: boolean;
    onClose: () => void;
    onFileDoubleClick?: (filePath: string) => void;
    hiddenFiles?: { path: string; reason: string }[];
    repoData?: GitHubRepo;
}

type TreeNode = {
    name: string;
    path: string;
    type: "blob" | "tree";
    children?: TreeNode[];
};

function buildTree(files: FileNode[]): TreeNode[] {
    const root: TreeNode[] = [];

    files.forEach((file) => {
        const parts = file.path.split("/");
        let currentLevel = root;
        let currentPath = "";

        parts.forEach((part, index) => {
            currentPath = currentPath ? `${currentPath}/${part}` : part;

            // Check if we already have this node at this level
            let existingNode = currentLevel.find((node) => node.name === part);

            if (!existingNode) {
                const isFile = index === parts.length - 1 && file.type === "blob";
                const newNode: TreeNode = {
                    name: part,
                    path: currentPath,
                    type: isFile ? "blob" : "tree",
                    children: isFile ? undefined : [],
                };

                currentLevel.push(newNode);
                existingNode = newNode;
            }

            if (existingNode.children) {
                currentLevel = existingNode.children;
            }
        });
    });

    // Sort: Folders first, then files
    const sortNodes = (nodes: TreeNode[]) => {
        nodes.sort((a, b) => {
            if (a.type === b.type) return a.name.localeCompare(b.name);
            return a.type === "tree" ? -1 : 1;
        });
        nodes.forEach((node) => {
            if (node.children) sortNodes(node.children);
        });
    };

    sortNodes(root);
    return root;
}

function FileTreeNode({
    node,
    depth,
    onFileDoubleClick,
    expandedPaths,
    onToggle
}: {
    node: TreeNode;
    depth: number;
    onFileDoubleClick?: (filePath: string) => void;
    expandedPaths: Set<string>;
    onToggle: (path: string) => void;
}) {
    const isFolder = node.type === "tree";
    const isExpanded = expandedPaths.has(node.path);

    const handleClick = () => {
        if (isFolder) {
            onToggle(node.path);
        } else if (onFileDoubleClick) {
            onFileDoubleClick(node.path);
        }
    };

    return (
        <div id={`sidebar-item-${node.path.replace(/\//g, '-')}`}>
            <div
                draggable
                onDragStart={(e) => {
                    e.dataTransfer.setData("text/plain", node.path);
                    e.dataTransfer.effectAllowed = "copy";
                }}
                className={cn(
                    "flex items-center gap-1.5 py-1 px-2 text-sm text-zinc-300 hover:text-white hover:bg-white/5 rounded cursor-pointer select-none transition-colors",
                    depth > 0 && "ml-3",
                    isExpanded && isFolder && "text-white"
                )}
                onClick={handleClick}
            >
                {isFolder && (
                    <span className="text-zinc-600">
                        {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    </span>
                )}

                {isFolder ? (
                    <FolderIcon name={node.name} isExpanded={isExpanded} />
                ) : (
                    <FileIcon filename={node.name} />
                )}

                <span className="truncate">{node.name}</span>
            </div>

            {isExpanded && node.children && (
                <div className="border-l border-white/5 ml-2.5">
                    {node.children.map((child) => (
                        <FileTreeNode
                            key={child.path}
                            node={child}
                            depth={depth + 1}
                            onFileDoubleClick={onFileDoubleClick}
                            expandedPaths={expandedPaths}
                            onToggle={onToggle}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

export function RepoSidebar({ fileTree, repoName, isOpen, onClose, onFileDoubleClick, hiddenFiles = [], repoData }: RepoSidebarProps) {
    const tree = buildTree(fileTree);
    const [showHiddenFiles, setShowHiddenFiles] = useState(false);
    const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

    const togglePath = (path: string) => {
        setExpandedPaths(prev => {
            const next = new Set(prev);
            if (next.has(path)) {
                next.delete(path);
            } else {
                next.add(path);
            }
            return next;
        });
    };

    useEffect(() => {
        const handleRevealFolder = (e: Event) => {
            const folderPath = (e as CustomEvent<string>).detail;
            if (!folderPath) return;

            // Expand all parents
            const parts = folderPath.split('/');
            const pathsToExpand: string[] = [];
            let current = '';
            parts.forEach(part => {
                current = current ? `${current}/${part}` : part;
                pathsToExpand.push(current);
            });

            setExpandedPaths(prev => {
                const next = new Set(prev);
                pathsToExpand.forEach(p => next.add(p));
                return next;
            });

            // Small delay to ensure the sidebar is open and DOM is updated
            setTimeout(() => {
                const elementId = `sidebar-item-${folderPath.replace(/\//g, '-')}`;
                const element = document.getElementById(elementId);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    // Visual feedback
                    element.classList.add('bg-blue-500/10');
                    setTimeout(() => element.classList.remove('bg-blue-500/10'), 2000);
                }
            }, 100);
        };

        window.addEventListener('reveal-folder', handleRevealFolder);
        return () => window.removeEventListener('reveal-folder', handleRevealFolder);
    }, []);

    return (
        <>
            {/* Mobile overlay */}
            {isOpen && (
                <div
                    className="md:hidden fixed inset-0 bg-black/50 z-40"
                    onClick={onClose}
                />
            )}

            {/* Sidebar */}
            <div className={cn(
                "w-64 max-w-[80vw] md:max-w-none border-r border-white/10 bg-zinc-900 flex flex-col h-full overflow-hidden transition-transform duration-300 ease-in-out",
                // Mobile: fixed and slide in/out
                "md:relative md:translate-x-0",
                "fixed z-50",
                isOpen ? "translate-x-0" : "-translate-x-full"
            )}>
                <div className="p-4 border-b border-white/10 bg-zinc-900 flex flex-col gap-3">
                    <div className="flex items-center justify-between w-full">
                        <h2 className="font-semibold text-white flex items-center gap-2 text-sm overflow-hidden">
                            <GitBranch className="w-4 h-4 text-purple-400 shrink-0" />
                            <span className="truncate" title={repoName}>{repoName}</span>
                        </h2>
                        {/* Close button for mobile */}
                        <button
                            onClick={onClose}
                            className="md:hidden p-1 hover:bg-white/10 rounded transition-colors shrink-0"
                        >
                            <X className="w-4 h-4 text-zinc-400" />
                        </button>
                    </div>

                    {repoData && (
                        <div className="space-y-3">
                            {repoData.description && (
                                <p className="text-xs text-zinc-400 line-clamp-2 leading-relaxed">
                                    {repoData.description}
                                </p>
                            )}

                            <div className="flex items-center justify-between text-xs text-zinc-500">
                                <div className="flex items-center gap-1" title="Stars">
                                    <Star className="w-3 h-3 text-yellow-500/70" />
                                    <span>{repoData.stargazers_count}</span>
                                </div>
                                <div className="flex items-center gap-1" title="Forks">
                                    <GitFork className="w-3 h-3 text-blue-400/70" />
                                    <span>{repoData.forks_count}</span>
                                </div>
                                <div className="flex items-center gap-1" title="Open Issues">
                                    <CircleDot className="w-3 h-3 text-green-400/70" />
                                    <span>{repoData.open_issues_count}</span>
                                </div>
                            </div>

                            <div className="flex items-center gap-1.5 text-[10px] text-zinc-600 uppercase tracking-wider font-medium">
                                <Calendar className="w-3 h-3" />
                                <span>Updated {new Date(repoData.updated_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="flex-1 overflow-y-auto p-2 scroll-smooth">
                    {tree.map((node) => (
                        <FileTreeNode
                            key={node.path}
                            node={node}
                            depth={0}
                            onFileDoubleClick={onFileDoubleClick}
                            expandedPaths={expandedPaths}
                            onToggle={togglePath}
                        />
                    ))}
                </div>

                {hiddenFiles.length > 0 && (
                    <div className="p-3 border-t border-white/10 bg-zinc-900/80 backdrop-blur-sm">
                        <button
                            onClick={() => setShowHiddenFiles(true)}
                            className="w-full flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors p-2 hover:bg-white/5 rounded"
                        >
                            <AlertCircle className="w-4 h-4 text-yellow-500/50" />
                            <span>{hiddenFiles.length} system files hidden</span>
                        </button>
                    </div>
                )}
            </div>

            {/* Hidden Files Modal */}
            {showHiddenFiles && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-zinc-900 border border-white/10 rounded-xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
                        <div className="p-4 border-b border-white/10 flex items-center justify-between bg-zinc-900/50">
                            <h3 className="font-semibold text-white flex items-center gap-2">
                                <AlertCircle className="w-4 h-4 text-yellow-500" />
                                Hidden Files
                            </h3>
                            <button
                                onClick={() => setShowHiddenFiles(false)}
                                className="p-1 hover:bg-white/10 rounded transition-colors"
                            >
                                <X className="w-4 h-4 text-zinc-400" />
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-2">
                            <p className="text-sm text-zinc-400 mb-4">
                                The following files and directories are hidden from the file tree to reduce noise and improve performance.
                            </p>
                            {hiddenFiles.map((file, i) => (
                                <div key={i} className="flex items-start justify-between gap-4 p-2 rounded bg-zinc-950/50 border border-white/5 text-sm">
                                    <span className="font-mono text-zinc-300 break-all">{file.path}</span>
                                    <span className="text-xs text-zinc-500 whitespace-nowrap">{file.reason}</span>
                                </div>
                            ))}
                        </div>
                        <div className="p-4 border-t border-white/10 bg-zinc-900/50">
                            <button
                                onClick={() => setShowHiddenFiles(false)}
                                className="w-full py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors text-sm font-medium"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
