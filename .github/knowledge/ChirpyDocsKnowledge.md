# General Chirpy + Jekyll Notes

## Purpose
Capture reusable guidance for working with jekyll-theme-chirpy and Jekyll-based documentation sites.

## Core concepts
- jekyll-theme-chirpy is a theme that expects site structure and theme data in specific places. Customizations should generally use theme override files under _layouts/ and _includes/ in the site source.
- Navigation in Chirpy is driven by site.tabs rather than page-level sidebar definitions. Each tab should include a `title`, `url`, and optional `icon`.
- Label text is localized through site.data.locales[lang]. If a locale entry is missing, Chirpy falls back to the raw `title` value for tabs and panels.
- Theme metadata such as `title`, `tagline`, and `favicon` are used directly by the sidebar and header.

## Recommended patterns
- Use layout: page for documentation pages and let site.tabs provide the main menu.
- Add a global `toc: true` setting in _config.yml when you want the Chirpy TOC panel available site-wide.
- Place shared theme overrides under source `_layouts/` and `_includes/`. These files shadow the installed theme gem automatically.
- Prefer pretty permalinks (/installation/, /cli/, etc.) for page URLs when using Chirpy’s default navigation.

## Common quirks
- The Chirpy TOC panel can require both site.toc: true and page.toc: true to display on regular pages.
- Built-in panel includes like `trending-tags.html` and `update-list.html` may assume `site.posts` exists. For documentation-only sites, override those includes to use `site.pages` instead.
- The `jekyll-last-modified-at` plugin attaches `page.last_modified_at` to pages, posts, and documents. That can break on non-content asset pages unless you guard or skip `assets/` paths.
- `jekyll-last-modified-at` often requires full Git history in CI, so use `fetch-depth: 0` in GitHub Actions if relying on git timestamps.
- Chirpy uses site.data.origin and _data/origin/ for asset URLs. Missing asset files can cause build failures if referenced by theme templates.

## Practical editing advice
- Inspect the theme’s installed _includes/ files before customizing layouts or panel behavior.
- Override only the specific includes or layouts you need, and preserve the theme’s default structure when possible.
- If you need a custom sidebar or panel, match Chirpy’s HTML pattern to avoid breaking theme CSS or JS.
- Keep localization keys aligned with site.data.locales[lang] when adding new tabs or panel labels.

## Validation guidance
- Run `bundle exec jekyll build` in the docs source to verify changes.
- When overriding `update-list.html` or `trending-tags.html`, test pages with and without tags to ensure the panel still renders correctly.
- If using `jekyll-last-modified-at`, confirm Git history is available and that asset files are not being processed as content pages.
