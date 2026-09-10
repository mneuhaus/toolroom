# Framework conventions

- This directory is the maintained framework workbench. Keep original project sources and installed skills intact unless migration is explicitly requested.
- Author filenames, code, skill entrypoints, all maintained documentation and website text in English. Preserve original source snapshots and historical evidence; translate their maintained explanations and captions.
- Keep common conventions in knowledge/, machine and style data in profiles/, short task routing in skills/. Preserve provenance for imported code and images.
- Edit Markdown and catalogue sources, then regenerate the static site with tools/build_site.py. The site must work offline and under a URL subdirectory.
- Preserve native-source authority, declared transforms, raw findings and incomplete analysis. A rendered example is not a physical acceptance result.
- For helper changes run relevant regression tests. For website changes inspect desktop and mobile layouts and the actual interactions.
- No live CAD, slicer job, device or publishing operation is required for documentation work.
