"use client";

import { DirectoryNode } from "@/types";
import {
    FileText,
    Search,
    ChevronRight,
    Folder,
    ExternalLink,
    Globe,
    Calendar
} from "lucide-react";
import { clsx } from "clsx";
import { useState, useMemo } from "react";

interface NodeDetailsProps {
    node: DirectoryNode;
    onNavigate: (pathSegment: string) => void;
}

const COMMON_PAGE_PATTERNS = [
    "login", "signup", "signin", "register", "cart", "account", "reset-password",
    "contact", "pricing", "legal", "policy", "terms", "about", "support",
    "faq", "help", "careers", "jobs", "status", "feed", "rss", "atom", "sitemap"
];

const LANGUAGE_MAP: Record<string, string> = {
    "ar": "阿拉伯语",
    "bg": "保加利亚语",
    "cs": "捷克语",
    "da": "丹麦语",
    "de": "德语",
    "el": "希腊语",
    "en": "英语",
    "es": "西班牙语",
    "et": "爱沙尼亚语",
    "fi": "芬兰语",
    "fr": "法语",
    "he": "希伯来语",
    "hi": "印地语",
    "hr": "克罗地亚语",
    "hu": "匈牙利语",
    "id": "印尼语",
    "it": "意大利语",
    "ja": "日语",
    "ko": "韩语",
    "lt": "立陶宛语",
    "lv": "拉脱维亚语",
    "nl": "荷兰语",
    "no": "挪威语",
    "pl": "波兰语",
    "pt": "葡萄牙语",
    "pt-br": "葡萄牙语(巴西)",
    "ro": "罗马尼亚语",
    "ru": "俄语",
    "sk": "斯洛伐克语",
    "sl": "斯洛文尼亚语",
    "sr": "塞尔维亚语",
    "sv": "瑞典语",
    "th": "泰语",
    "tr": "土耳其语",
    "uk": "乌克兰语",
    "vi": "越南语",
    "zh": "中文",
    "zh-cn": "中文(简体)",
    "zh-tw": "中文(繁体)"
};

export function NodeDetails({ node, onNavigate }: NodeDetailsProps) {
    const [hideCommon, setHideCommon] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");

    const isNoise = (name: string) => {
        const lower = name.toLowerCase();
        return COMMON_PAGE_PATTERNS.some(p => lower.includes(p));
    };

    const isLanguage = (name: string) => {
        return Object.keys(LANGUAGE_MAP).includes(name.toLowerCase());
    }

    const filteredRecords = useMemo(() => {
        return node.records.filter(record => {
            if (hideCommon && isNoise(record.path)) return false;

            if (searchQuery) {
                const q = searchQuery.toLowerCase();
                return (
                    record.path.toLowerCase().includes(q) ||
                    (record.title || "").toLowerCase().includes(q) ||
                    record.action.toLowerCase().includes(q) ||
                    record.object.toLowerCase().includes(q)
                );
            }
            return true;
        });
    }, [node.records, hideCommon, searchQuery]);

    // Split Sub-directories into Standard and Languages
    const { standardDirs, languageDirs } = useMemo(() => {
        let dirs = [...(node.children || [])];

        if (hideCommon) {
            dirs = dirs.filter(d => !isNoise(d.name));
        }

        const standard = dirs.filter(d => !isLanguage(d.name)).sort((a, b) => a.name.localeCompare(b.name));
        const langs = dirs.filter(d => isLanguage(d.name)).sort((a, b) => a.name.localeCompare(b.name));

        return { standardDirs: standard, languageDirs: langs };
    }, [node.children, hideCommon]);

    return (
        <div className="space-y-8">
            {/* Standard Sub-directories List (Competitor Style) */}
            {standardDirs.length > 0 && (
                <div>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                            <Folder className="w-4 h-4 text-blue-400" />
                            Sub-directories
                            <span className="text-slate-500 font-normal ml-2">({standardDirs.length})</span>
                        </h3>
                    </div>

                    <div className="flex flex-col gap-3">
                        {standardDirs.map(child => (
                            <DirectoryListItem
                                key={child.path}
                                node={child}
                                onNavigate={onNavigate}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Language Separator */}
            {standardDirs.length > 0 && languageDirs.length > 0 && <div className="border-t border-slate-800/50"></div>}

            {/* Language Directories Grid */}
            {languageDirs.length > 0 && (
                <div>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                            <Globe className="w-4 h-4 text-purple-400" />
                            Languages / 多语言站点
                            <span className="text-slate-500 font-normal ml-2">({languageDirs.length})</span>
                        </h3>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {languageDirs.map(child => (
                            <DirectoryCard
                                key={child.path}
                                name={child.name}
                                count={child.count}
                                label={LANGUAGE_MAP[child.name.toLowerCase()]}
                                icon={<Globe className="w-4 h-4 text-slate-500 group-hover:text-purple-400 transition-colors flex-shrink-0" />}
                                onClick={() => onNavigate(child.name)}
                                hoverColor="purple"
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Content Separator */}
            {(standardDirs.length > 0 || languageDirs.length > 0) && filteredRecords.length > 0 && <div className="border-t border-slate-800/50"></div>}

            {/* Pages Section */}
            {filteredRecords.length > 0 && (
                <div>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                            <FileText className="w-4 h-4 text-blue-400" />
                            Pages
                            <span className="text-slate-500 font-normal ml-2">({filteredRecords.length})</span>
                        </h3>

                        <div className="flex items-center gap-3">
                            <div className="relative">
                                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
                                <input
                                    type="text"
                                    placeholder="Search..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="bg-slate-900 border border-slate-800 rounded-md pl-8 pr-3 py-1 text-xs text-slate-200 focus:outline-none focus:border-blue-500/50 w-40 transition-colors"
                                />
                            </div>
                            <button
                                className={clsx(
                                    "text-xs px-2 py-1 rounded border transition-colors",
                                    hideCommon ? "bg-blue-500/10 text-blue-400 border-blue-500/20" : "bg-slate-900 text-slate-500 border-slate-800 hover:border-slate-700"
                                )}
                                onClick={() => setHideCommon(!hideCommon)}
                            >
                                {hideCommon ? "Noise: Hidden" : "Noise: Show"}
                            </button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        {filteredRecords.map((record) => (
                            <RecordItem key={record.url} record={record} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}



function DirectoryCard({ name, count, label, icon, onClick, hoverColor = "blue" }: {
    name: string,
    count: number,
    label?: string,
    icon?: React.ReactNode,
    onClick: () => void,
    hoverColor?: "blue" | "purple"
}) {
    const hoverClass = hoverColor === "purple" ? "hover:bg-purple-600/10 hover:border-purple-500/30" : "hover:bg-blue-600/10 hover:border-blue-500/30";
    const textGroupHover = hoverColor === "purple" ? "group-hover:text-purple-100" : "group-hover:text-blue-100";
    const chevronHover = hoverColor === "purple" ? "group-hover:text-purple-400" : "group-hover:text-blue-400";

    return (
        <div
            onClick={onClick}
            className={`group flex items-center justify-between p-3 bg-slate-900/40 border border-slate-800 rounded-lg cursor-pointer transition-all ${hoverClass}`}
        >
            <div className="flex items-center gap-3 overflow-hidden">
                {icon || <Folder className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition-colors flex-shrink-0" />}
                <div className="min-w-0 flex flex-col">
                    <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium text-slate-300 truncate block ${textGroupHover}`}>
                            {name}
                        </span>
                        {label && <span className="text-xs text-slate-500">({label})</span>}
                    </div>
                </div>
            </div>
            <div className="flex items-center gap-2">
                <span className={`text-xs text-slate-600 bg-slate-950/50 px-1.5 py-0.5 rounded ${hoverColor === 'purple' ? 'group-hover:text-purple-300/70' : 'group-hover:text-blue-300/70'}`}>
                    {count}
                </span>
                <ChevronRight className={`w-3 h-3 text-slate-700 opacity-0 group-hover:opacity-100 transition-all -ml-1 ${chevronHover}`} />
            </div>
        </div>
    )
}

function Badge({ label, variant }: { label: string, variant: 'intent' | 'default' }) {
    if (!label || label === 'unknown') return null;

    // Minimalist Badge
    const colors: Record<string, string> = {
        "commercial": "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
        "informational": "text-blue-400 bg-blue-400/10 border-blue-400/20",
        "navigational": "text-purple-400 bg-purple-400/10 border-purple-400/20",
    };

    let style = "text-slate-500 bg-slate-500/10 border-slate-500/20";
    for (const key in colors) {
        if (label.includes(key)) style = colors[key];
    }

    return (
        <span className={clsx("px-1.5 py-0.5 rounded text-[9px] uppercase font-bold tracking-wider border", style)}>
            {label}
        </span>
    );
}

// Update LeafDirectoryCard to show indication too (simplified)
function LeafDirectoryCard({ node }: { node: DirectoryNode }) {
    const [expanded, setExpanded] = useState(false);
    const record = node.records[0];
    const isNew = record.is_new;

    return (
        <div
            onClick={() => setExpanded(!expanded)}
            className={clsx(
                "group relative p-3 bg-slate-900/40 border rounded-lg cursor-pointer transition-all overflow-hidden",
                expanded ? "border-blue-500/50 bg-blue-900/10 shadow-lg shadow-blue-500/5 row-span-2" : "border-slate-800 hover:border-blue-500/30 hover:bg-slate-800/50",
                isNew && !expanded && "border-l-2 border-l-emerald-500"
            )}
        >
            {isNew && (
                <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse shadow-lg shadow-emerald-500/50"></div>
            )}
            <div className="flex flex-col gap-1">
                {/* Top: Small Folder Name */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                        <Folder className="w-3 h-3" />
                        /{node.name}
                    </div>
                    <ChevronRight className={clsx("w-3 h-3 text-slate-600 transition-transform", expanded && "rotate-90 text-blue-400")} />
                </div>

                {/* Main: Big Page Title */}
                <div className="text-sm font-bold text-slate-200 group-hover:text-blue-100 mt-1 line-clamp-2">
                    {record.title || "Untitled Page"}
                </div>

                {/* Expanded Details */}
                {expanded && (
                    <div className="mt-3 pt-3 border-t border-slate-700/50 space-y-3 animate-in fade-in slide-in-from-top-1 duration-200">
                        <div className="flex items-center gap-2 flex-wrap">
                            {isNew && <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">NEW</span>}
                            <Badge label={record.intent_category} variant="intent" />
                            {record.lastmod && (
                                <span className="text-[10px] text-slate-500 flex items-center gap-1">
                                    <Calendar className="w-3 h-3" />
                                    {record.lastmod.split("T")[0]}
                                </span>
                            )}
                        </div>

                        <a
                            href={record.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 hover:underline bg-blue-500/10 p-2 rounded border border-blue-500/20"
                        >
                            <ExternalLink className="w-3 h-3" />
                            Visit Page
                        </a>
                    </div>
                )}
            </div>
        </div>
    )
}

// Competitor Style List Item
function DirectoryListItem({ node, onNavigate }: { node: DirectoryNode, onNavigate: (p: string) => void }) {
    const [expanded, setExpanded] = useState(false);

    // Content to show when expanded
    const records = node.records || [];
    const hasChildren = node.children && node.children.length > 0;

    // Header Data
    const itemCount = node.count;

    return (
        <div className="bg-slate-900/30 border border-slate-800/60 rounded-lg overflow-hidden transition-all hover:border-blue-500/30">
            {/* Header Row */}
            <div
                onClick={() => setExpanded(!expanded)}
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-800/30 group"
            >
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                        <span className={clsx("text-lg font-bold group-hover:underline decoration-blue-500/50 underline-offset-4 truncate", expanded ? "text-blue-400" : "text-blue-400/90")}>
                            {node.name}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-5 pl-4">
                    <span className="text-xs text-slate-500 font-medium whitespace-nowrap">
                        {itemCount} items
                    </span>
                    <ChevronRight className={clsx("w-5 h-5 text-slate-600 transition-transform duration-200 flex-shrink-0", expanded && "rotate-90 text-blue-400")} />
                </div>
            </div>

            {/* Expanded Content */}
            {expanded && (
                <div className="border-t border-slate-800/50 bg-slate-950/30 p-4 animate-in fade-in slide-in-from-top-2 duration-200">
                    {/* List Pages */}
                    {records.length > 0 && (
                        <div className="flex flex-col gap-3">
                            {records.map(r => (
                                <RecordItem key={r.url} record={r} isExample />
                            ))}
                        </div>
                    )}

                    {/* Recursive Sub-folders */}
                    {hasChildren && (
                        <div className="flex flex-col gap-3 mt-3 ml-2 pl-4 border-l border-slate-800">
                            {node.children.map(child => (
                                <DirectoryListItem key={child.path} node={child} onNavigate={onNavigate} />
                            ))}
                        </div>
                    )}

                    {records.length === 0 && !hasChildren && (
                        <div className="p-4 text-center text-slate-500 text-sm italic">
                            Empty directory
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

function RecordItem({ record, isExample = false }: { record: any, isExample?: boolean }) {
    const displayUrl = record.url.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const lastMod = record.lastmod ? record.lastmod.split("T")[0] : "";

    return (
        <div className={clsx(
            "flex flex-col gap-2 group",
            isExample ? "" : "p-4 bg-slate-900/20 hover:bg-slate-800/40 border border-slate-800/50 hover:border-slate-700 rounded-lg transition-colors"
        )}>
            {/* Title Row - Only show if NOT an expanded child (isExample=false) */}
            {!isExample && (
                <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <a
                            href={record.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-semibold text-slate-200 hover:text-blue-400 hover:underline decoration-blue-500/30 underline-offset-4 transition-colors line-clamp-1"
                        >
                            {record.title || "Untitled Page"}
                        </a>
                        <Badge label={record.intent_category} variant="intent" />
                    </div>

                    <a
                        href={record.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-slate-700/50 rounded"
                    >
                        <ExternalLink className="w-3.5 h-3.5 text-slate-400 hover:text-blue-400" />
                    </a>
                </div>
            )}

            {/* URL Bubble Row + Date */}
            <div className="pl-0 flex items-center gap-3 flex-wrap">
                <a
                    href={record.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-100/5 hover:bg-slate-100/10 border border-slate-700/50 hover:border-blue-500/30 rounded-full transition-all group/url max-w-full"
                >
                    <span className="text-xs font-mono text-slate-400 group-hover/url:text-blue-300 truncate">
                        {displayUrl}/
                    </span>
                    <ExternalLink className="w-3 h-3 text-slate-600 group-hover/url:text-blue-400 flex-shrink-0" />
                </a>

                {record.is_new && (
                    <span className="flex items-center gap-1.5 px-1.5 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-bold text-emerald-400 animate-pulse">
                        NEW
                    </span>
                )}

                {lastMod && (
                    <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1.5">
                        <span className="w-1 h-1 bg-slate-700 rounded-full"></span>
                        Updated {lastMod}
                    </span>
                )}
            </div>
        </div>
    );
}


