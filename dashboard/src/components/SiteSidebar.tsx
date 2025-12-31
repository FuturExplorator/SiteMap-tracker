import { SitemapSummary } from "@/types";
import { LayoutGrid, Globe } from "lucide-react";
import { clsx } from "clsx";

interface SiteSidebarProps {
    sites: Record<string, SitemapSummary>;
    activeSite: string;
    onSelectSite: (site: string) => void;
}

export function SiteSidebar({ sites, activeSite, onSelectSite }: SiteSidebarProps) {
    return (
        <div className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col h-screen">
            <div className="p-4 border-b border-slate-800 flex items-center gap-2">
                <LayoutGrid className="w-5 h-5 text-blue-500" />
                <h1 className="font-bold text-slate-100 tracking-tight">Sitemap Tracker</h1>
            </div>

            <div className="p-4">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 px-2">
                    Websites
                </div>
                <div className="space-y-1">
                    {Object.keys(sites).map((siteDomain) => (
                        <button
                            key={siteDomain}
                            onClick={() => onSelectSite(siteDomain)}
                            className={clsx(
                                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                                activeSite === siteDomain
                                    ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
                                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                            )}
                        >
                            <div className={clsx(
                                "w-8 h-8 rounded flex items-center justify-center transition-colors",
                                activeSite === siteDomain ? "bg-white/20" : "bg-slate-800 group-hover:bg-slate-700"
                            )}>
                                <Globe className="w-4 h-4" />
                            </div>
                            <span className="truncate">{siteDomain}</span>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
