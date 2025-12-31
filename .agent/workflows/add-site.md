---
description: Add a new website to the Sitemap Tracker dashboard
---
1. Run the backend tracker to fetch data:
    ```bash
    # Replace with your target domain
    python3 -m sitemap_tools.cli intent-map --sitemap-url https://example.com/sitemap.xml --output-dir output
    ```

2. Copy the generated data to the dashboard:
    ```bash
    # Replace example.com with the actual domain folder created
    cp output/sites/example.com/latest/intent_summary.json dashboard/src/data/example.json
    ```

3. Register the new site in the Dashboard code:
    - Open `dashboard/src/app/page.tsx`
    - Import the new JSON: `import exampleData from "@/data/example.json";`
    - Add to `SITES` object: `"example.com": exampleData as unknown as SitemapSummary,`

4. (Optional) Restart dev server if needed, though usually hot reload handles it.
