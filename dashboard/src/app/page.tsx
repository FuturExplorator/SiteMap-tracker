"use client";

import { useState, useMemo } from "react";
import unblurData from "@/data/unblurimage.json";
import kreaData from "@/data/krea.json";
import galaxyData from "@/data/galaxy.json";
import { SitemapSummary, DirectoryNode, IntentRecord } from "@/types";
import {
  PieChart,
  Activity,
  FileText,
  ChevronRight,
  Home,
  LayoutGrid,
  Library,
  FolderTree,
  ListFilter,
  ArrowUpDown,
  Sparkles
} from "lucide-react";
import { SiteSidebar } from "@/components/SiteSidebar";
import { NodeDetails } from "@/components/NodeDetails";

const SITES: Record<string, SitemapSummary> = {
  "unblurimage.ai": unblurData as unknown as SitemapSummary,
  "krea.ai": kreaData as unknown as SitemapSummary,
  "galaxy.ai": galaxyData as unknown as SitemapSummary,
};

type ViewMode = 'structure' | 'intent' | 'media';
type SortMode = 'name' | 'date' | 'count';

// --- Data Transformation Helpers ---

function getAllRecords(node: DirectoryNode): IntentRecord[] {
  let records = [...node.records];
  // Recursively collect from children
  for (const child of node.children) {
    records = records.concat(getAllRecords(child));
  }
  return records;
}

function groupRecords(records: IntentRecord[], keyFn: (r: IntentRecord) => string, sortMode: SortMode): DirectoryNode {
  const groups: Record<string, IntentRecord[]> = {};

  for (const rec of records) {
    const key = keyFn(rec) || "Uncategorized";
    if (!groups[key]) groups[key] = [];
    groups[key].push(rec);
  }

  const children: DirectoryNode[] = Object.entries(groups).map(([name, groupRecords]) => ({
    name,
    path: `/${name}`, // Virtual path
    count: groupRecords.length,
    children: [], // Flat groups don't have sub-folders usually
    records: groupRecords.sort((a, b) => {
      if (sortMode === 'date') return (b.lastmod || "").localeCompare(a.lastmod || "");
      return (a.title || a.url).localeCompare(b.title || b.url);
    })
  }));

  // Sort the groups themselves
  children.sort((a, b) => {
    if (sortMode === 'count') return b.count - a.count;
    if (sortMode === 'date') {
      // Approximate group date by latest item? Expensive. Let's stick to name or count for groups.
      return b.count - a.count; // Default desc count for meaningful groups
    }
    return a.name.localeCompare(b.name);
  });

  return {
    name: "Root",
    path: "/",
    count: records.length,
    children,
    records: []
  };
}


export default function Dashboard() {
  const [activeSite, setActiveSite] = useState<string>("krea.ai");
  const [viewMode, setViewMode] = useState<ViewMode>('structure');
  const [sortMode, setSortMode] = useState<SortMode>('name');
  const [navigationPath, setNavigationPath] = useState<string[]>([]);

  const data = SITES[activeSite];

  // 1. Get Base Data (Raw Tree or Flattened List)
  const baseRecords = useMemo(() => getAllRecords(data.directory_tree), [data]);

  // 2. Transform into a "Virtual Root Node" based on ViewMode
  const virtualRoot = useMemo(() => {
    if (viewMode === 'structure') {
      // Deep clone to avoid mutating original if needed, or just extend
      return {
        ...data.directory_tree,
        name: activeSite
      };
    } else if (viewMode === 'intent') {
      return groupRecords(baseRecords, r => r.intent_category, sortMode);
    } else { // media
      return groupRecords(baseRecords, r => r.object, sortMode);
    }
  }, [data, viewMode, sortMode, baseRecords, activeSite]);

  // 3. Navigate the Virtual Tree
  const currentNode = useMemo(() => {
    let current = virtualRoot;
    // Navigation path logic works the same for Virtual Nodes (Level 1 is category, Level 2 is empty)
    for (const segment of navigationPath) {
      const child = current.children.find(c => c.name === segment);
      if (child) {
        current = child;
      } else {
        return virtualRoot;
      }
    }
    return current;
  }, [virtualRoot, navigationPath]);

  // View Switch Reset
  const handleViewSwitch = (mode: ViewMode) => {
    setViewMode(mode);
    setNavigationPath([]); // Reset nav when changing perspective
  }

  const handleSiteSwitch = (site: string) => {
    setActiveSite(site);
    setNavigationPath([]);
    // Keep current view mode
  };

  const newUrlCount = useMemo(() => baseRecords.filter(r => r.is_new).length, [baseRecords]);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      <SiteSidebar
        sites={SITES}
        activeSite={activeSite}
        onSelectSite={handleSiteSwitch}
      />

      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header KPI */}
        <div className="px-8 py-6 border-b border-slate-800 bg-slate-950/50 backdrop-blur-sm z-10">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <StatsCard title="Total URLs" value={data.total_urls} icon={<FileText className="h-4 w-4 text-blue-400" />} />
            <StatsCard
              title="New Arrivals"
              value={newUrlCount}
              subValue={newUrlCount > 0 ? "Since last snapshot" : "Up to date"}
              icon={<Sparkles className="h-4 w-4 text-amber-400" />}
              highlight={newUrlCount > 0}
            />
            <StatsCard title="Intent Categories" value={data.by_intent_category.length} icon={<PieChart className="h-4 w-4 text-purple-400" />} />
            <StatsCard title="Strict Coverage" value={`${data.coverage_strict_percentage}%`} subValue="Action + Object" icon={<Activity className="h-4 w-4 text-green-400" />} />
            <StatsCard title="Any Coverage" value={`${data.coverage_any_percentage}%`} subValue="Partial Match" icon={<Activity className="h-4 w-4 text-yellow-400" />} />
          </div>
        </div>

        {/* Toolbar & Breadcrumbs */}
        <div className="px-8 py-3 border-b border-slate-800 bg-slate-900/40 flex items-center justify-between text-sm">
          {/* Breadcrumbs */}
          <div className="flex items-center">
            <button
              onClick={() => setNavigationPath([])}
              className={`flex items-center hover:text-blue-400 transition-colors ${navigationPath.length === 0 ? 'text-blue-400 font-semibold' : 'text-slate-400'}`}
            >
              <Home className="w-4 h-4 mr-1" />
              {viewMode === 'structure' ? 'Home' : viewMode === 'intent' ? 'All Intents' : 'All Media'}
            </button>
            {navigationPath.map((segment, index) => (
              <div key={index} className="flex items-center">
                <ChevronRight className="w-4 h-4 text-slate-600 mx-2" />
                <button
                  onClick={() => setNavigationPath(navigationPath.slice(0, index + 1))}
                  className={`hover:text-blue-400 transition-colors ${index === navigationPath.length - 1 ? 'text-blue-400 font-semibold' : 'text-slate-400'}`}
                >
                  {segment}
                </button>
              </div>
            ))}
          </div>

          {/* Controls */}
          <div className="flex items-center gap-4">
            {/* View Switcher */}
            <div className="flex items-center bg-slate-800/50 rounded-lg p-1 border border-slate-700/50">
              <ViewTab active={viewMode === 'structure'} onClick={() => handleViewSwitch('structure')} icon={FolderTree} label="Structure" />
              <ViewTab active={viewMode === 'intent'} onClick={() => handleViewSwitch('intent')} icon={LayoutGrid} label="Intent" />
              <ViewTab active={viewMode === 'media'} onClick={() => handleViewSwitch('media')} icon={Library} label="Media" />
            </div>

            {/* Sort Dropdown (Simple Toggle for now) */}
            <button
              onClick={() => setSortMode(prev => prev === 'name' ? 'count' : 'name')}
              className="flex items-center gap-2 px-3 py-1.5 text-slate-400 hover:text-slate-200 text-xs font-medium bg-slate-800/30 hover:bg-slate-800 rounded border border-slate-700/30 transition-all"
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
              Sort by: {sortMode === 'name' ? 'Name' : 'Count'}
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
          <div className="max-w-6xl mx-auto pb-12">
            <h2 className="text-3xl font-bold mb-2 text-slate-100 flex items-center gap-3">
              {currentNode.name === activeSite ? "Root Directory" : currentNode.name}
              {viewMode !== 'structure' && navigationPath.length === 0 && (
                <span className="text-base font-normal text-slate-500 px-3 py-1 bg-slate-800/50 rounded-full border border-slate-700/50">
                  {viewMode === 'intent' ? 'Grouped by Intent Category' : 'Grouped by Object Type'}
                </span>
              )}
            </h2>

            <div className="mt-6 bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
              <NodeDetails
                node={currentNode}
                onNavigate={(path) => setNavigationPath([...navigationPath, path])}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatsCard({ title, value, subValue, icon, highlight }: { title: string, value: string | number, subValue?: string, icon: any, highlight?: boolean }) {
  return (
    <div className={`bg-slate-900/50 border rounded-lg flex flex-col justify-between h-24 p-3 transition-colors ${highlight ? 'border-amber-500/30 bg-amber-500/5' : 'border-slate-800'}`}>
      <div className="flex items-center justify-between">
        <div className={`text-xs font-medium uppercase tracking-wide ${highlight ? 'text-amber-400' : 'text-slate-400'}`}>{title}</div>
        {icon}
      </div>
      <div>
        <div className={`text-xl font-bold ${highlight ? 'text-amber-100' : 'text-slate-100'}`}>{value}</div>
        {subValue && <div className="text-[10px] text-slate-500 mt-0.5">{subValue}</div>}
      </div>
    </div>
  )
}

function ViewTab({ active, onClick, icon: Icon, label }: { active: boolean, onClick: () => void, icon: any, label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${active
          ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
        }`}
    >
      <Icon className="w-3.5 h-3.5" />
      {label}
    </button>
  )
}
