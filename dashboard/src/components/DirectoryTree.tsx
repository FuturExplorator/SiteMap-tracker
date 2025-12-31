"use client";

import { useState } from "react";
import { DirectoryNode } from "@/types";
import {
    Folder,
    FolderOpen,
    ChevronRight,
    ChevronDown,
    Globe
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx } from "clsx";

interface DirectoryTreeProps {
    node: DirectoryNode;
    onSelect: (node: DirectoryNode) => void;
    selectedPath: string;
    level?: number;
}

export function DirectoryTree({ node, onSelect, selectedPath, level = 0 }: DirectoryTreeProps) {
    const [isOpen, setIsOpen] = useState(level < 1); // Open root by default
    const hasChildren = node.children && node.children.length > 0;

    const isSelected = node.path === selectedPath;

    const handleToggle = (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsOpen(!isOpen);
        onSelect(node);
    };

    const handleSelect = (e: React.MouseEvent) => {
        e.stopPropagation();
        onSelect(node);
    };

    return (
        <div className="select-none">
            <div
                className={clsx(
                    "flex items-center gap-1.5 py-1 px-2 rounded-md cursor-pointer transition-colors text-sm",
                    isSelected
                        ? "bg-blue-500/20 text-blue-200"
                        : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
                )}
                style={{ paddingLeft: `${level * 12 + 8}px` }}
                onClick={handleSelect}
            >
                <button
                    onClick={handleToggle}
                    className={clsx(
                        "p-0.5 rounded-sm hover:bg-slate-700/50 transition-colors",
                        !hasChildren && "opacity-0 pointer-events-none"
                    )}
                >
                    {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                </button>

                <span className="text-slate-500">
                    {hasChildren ? (
                        isOpen ? <FolderOpen className="w-4 h-4 text-amber-500/80" /> : <Folder className="w-4 h-4 text-amber-500/80" />
                    ) : (
                        <Globe className="w-3.5 h-3.5 text-slate-600" />
                    )}
                </span>

                <span className="truncate">{node.name}</span>

                {node.count > 0 && (
                    <span className="ml-auto text-xs text-slate-600 font-mono bg-slate-900/50 px-1.5 py-0.5 rounded-full">
                        {node.count}
                    </span>
                )}
            </div>

            <AnimatePresence initial={false}>
                {isOpen && hasChildren && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        {node.children.map((child) => (
                            <DirectoryTree
                                key={child.path}
                                node={child}
                                onSelect={onSelect}
                                selectedPath={selectedPath}
                                level={level + 1}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
