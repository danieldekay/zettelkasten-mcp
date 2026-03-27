---
description: "All Markdown files in the docs/ folder must start with a project knowledge header"
applyTo: "docs/**/*.md"
---

## Project Knowledge File Header

Every Markdown file inside `docs/` must begin with the following header block,
placed **before** any other content (including front matter titles or headings):

```
================================================================
Start of Project Knowledge File
================================================================

Purpose:
--------
This file is designed to be consumed by AI systems for analysis, review,
or other automated processes. It solely serves the purpose of background
information and should NOT under any circumstances leak into the user's
interaction with the AI when actually USING the Zettelkasten MCP tools to
process, explore or synthesize user-supplied information.

Content:
--------
```

And must end with:

```
================================================================
End of Project Knowledge File
================================================================
```

### Rules

- The opening header block must be the very first lines of the file.
- Do not place a Markdown `#` heading or YAML front matter before the header.
- The `Content:` section marker separates the header from the actual document body.
- The closing footer must be the very last lines of the file (no trailing blank lines after it).
- When **creating** a new `docs/**/*.md` file, scaffold it with header + footer already in place.
- When **editing** an existing file that is missing the header, add it before making any other changes.
