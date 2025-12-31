export interface IntentRecord {
    url: string;
    path: string;
    depth?: number; // mapped from path_depth
    slug_tokens?: string[];
    action: string;
    object: string;
    scene?: string;
    intent_category: string;
    notes?: string;
    lastmod: string | null;
    title?: string; // Inferred title
    is_new?: boolean;
}

export interface DirectoryNode {
    name: string;
    path: string;
    count: number;
    children: DirectoryNode[];
    records: IntentRecord[];
}

export interface IntentGroup {
    intent_category: string;
    url_count: number;
    sample_urls: string[];
}

export interface ActionObjectGroup {
    action: string;
    object: string;
    url_count: number;
    sample_urls: string[];
}

export interface SitemapSummary {
    schema_version: string;
    by_intent_category: IntentGroup[];
    by_action_object: ActionObjectGroup[];
    total_urls: number;
    coverage_strict_percentage: number;
    coverage_any_percentage: number;
    directory_tree: DirectoryNode;
}
