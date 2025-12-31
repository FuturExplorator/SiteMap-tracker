# Sitemap Tracker & Analytics (FuturExplorator)

A comprehensive tool for tracking, analyzing, and visualizing website sitemaps over time. It transforms flat URL lists into structured, actionable insights about a competitor's product strategy and content updates.

## Key Capabilities

### 1. Automated Sitemap Analysis (CMS Agnostic)
- **Auto-Discovery**: Automatically finds sitemaps via `robots.txt` or common paths.
- **Recursive Parsing**: Handles deeply nested sitemap indexes.
- **Intent Classification**: Uses rule-based logic (and optional LLM) to tag every URL with:
  - **Intent**: Users' goal (e.g., `remove-background`, `upscale`, `login`).
  - **Object**: Target asset (e.g., `face`, `audio`, `video`).
  - **Action**: Operation (e.g., `generate`, `compress`).

### 2. Historical Tracking & Diffing
- **Snapshots**: Saves full site structure versions in `output/sites/<domain>/history/`.
- **Change Detection**: Automatically identifying **New** and **Removed** URLs since the last visit.
- **"New" Badging**: Dashboard highlights fresh content with pulsing green badges.

### 3. Interactive Dashboard (Next.js)
A modern, dark-mode visualization tool to explore the data.

#### **Three Powerful Views**
1.  **📁 Structure View (Tree)**:
    - Browse the physical URL hierarchy (e.g., `/features/edit/face`).
    - **In-Place Expansion**: Deeply nested folders expand directly in the tree for seamless browsing.
    - **Leaf Node Counts**: Quickly see how large each section is.

2.  **🏷️ Intent View (Functional)**:
    - Groups pages by *User Intent* (e.g., "All Upscaling Tools", "All Generators").
    - Ignores URL structure to show what the product *does*.
    - Sort by **Count** to see the biggest feature sets.

3.  **🎬 Media View (Asset-Based)**:
    - Groups pages by the *Object* they handle (e.g., "Image", "Video", "Text").
    - Ideal for understanding a competitor's media focus.

#### **Rich Filtering & Sorting**
- **Sort By**: Name (A-Z) or Count (size of category).
- **New Arrivals**: filter/highlight only new content.

## Quick Start

### 1. Run the Backend (Python)
Extract data from a site (e.g., Krea.ai):

```bash
# Basic run (fetches, classifies, updates history)
python -m sitemap_tools cli run --domain krea.ai
```

### 2. Launch the Dashboard
Visualize the data:

```bash
cd dashboard
npm run dev
# Open http://localhost:3000
```

## Project Structure
- `sitemap_tools/`: Python core logic (fetching, intent classification, diffing).
- `dashboard/`: Next.js frontend (visualization, state management).
- `output/sites/`: Data storage (JSON/CSV snapshots organized by domain).
