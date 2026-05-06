---
name: zettelkasten-philosophy
description: >
  Zettelkasten theory, principles, and best practices from Luhmann through modern digital
  implementations. Covers atomicity, typed linking, note type selection, emergence,
  anti-patterns, and AI integration. Use when deciding how to structure notes, which link
  type to choose, how to grow a healthy knowledge graph, or when onboarding to ZK thinking.
  Triggers: "Zettelkasten best practices", "which note type", "how to link notes",
  "atomic notes", "Luhmann", "ZK philosophy", "knowledge graph", "evergreen notes",
  "collector's fallacy", "ZK anti-patterns".
author: Daniel Kaesmayr
metadata:
  version: "1.0.0"
  category: knowledge-management
  repo: https://github.com/entanglr/zettelkasten-mcp
references:
  - title: "Zettelkasten method — Gianmarco David"
    url: https://gianmarcodavid.com/posts/zettelkasten/
  - title: "How To Take Smart Notes — Scrintal"
    url: https://scrintal.com/guides/how-to-take-smart-notes
  - title: "Zettelkasten 101 — Sloww"
    url: https://www.sloww.co/zettelkasten/
  - title: "Niklas Luhmann's Card Index: The Fabrication of Serendipity"
    url: https://sociologica.unibo.it/article/view/8350/8272
  - title: "Proper Care for a Digital Zettelkasten"
    url: https://www.latematinee.com/p/proper-care-for-a-digital-zettelkasten
  - title: "A Beginner's Guide to the Zettelkasten Method — Zenkit"
    url: https://zenkit.com/en/blog/a-beginners-guide-to-the-zettelkasten-method/
---

# Zettelkasten Philosophy

Theory and best practices for building a healthy, generative knowledge graph.

---

## The Three Core Principles

### 1. Atomicity

**One idea per note.**

Each note should express exactly one thought, claim, or insight. Long notes break later linking: you can't precisely point to "the claim about X" if it's buried in a page about ABCXYZ.

A useful test: can you link to this note without qualification?
- ✅ "This supports [[Claim About X]]" — the note *is* the claim
- ❌ "See the third paragraph of [[Long Note About Everything]]"

**Practical rule:** If a note needs subsections, it has multiple ideas. Split it.

### 2. Connectivity

**Links over folders. Typed links over tags.**

Luhmann's original system had no categories — only links. The power comes not from where a note is stored, but from how it is connected. A note with zero links is effectively invisible to future thinking.

**Aim:** ≥ 2 links per permanent note. If you can't find anything to link, search harder or the note may be too vague to be useful.

**Typed links beat plain hyperlinks** because they encode *why* two ideas are related:
- `supports` tells you this note provides evidence
- `contradicts` tells you there's a tension worth exploring
- `extends` tells you this note builds a foundation further

### 3. Emergence

**Patterns you didn't plan appear through traversal.**

The graph is generative. Insights emerge when you browse links across domains, not when you file notes into folders. Luhmann called this the *serendipity* of the card index — his system "surprised" him by connecting concepts he hadn't consciously related.

> "Luhmann's card index allows the production of new and often unexpected knowledge by relating concepts and thoughts that do not have much in common at first."
> — Schmidt, "Niklas Luhmann's Card Index: The Fabrication of Serendipity"

This only works if you actually follow links. Schedule exploration sessions, not just capture sessions.

---

## Note Types: What to Use When

| Type | When to use | Lifespan |
|---|---|---|
| `fleeting` | Quick capture of transient thoughts; shower ideas; in-meeting jottings | Hours → days. Process or delete; never let them accumulate |
| `literature` | Processing a specific source (paper, book, article, talk) | Long-term; one note per source |
| `permanent` | A single distilled, own-words claim ready to link and build on | Permanent; your knowledge atoms |
| `structure` | Entry points into a topic cluster; Maps of Content (MOCs); indexes | Evolves as the topic grows |
| `hub` | Highest-level entry points; major themes or research programs | Rare; only when a structure note needs a structure note |

**Fleeting notes are temporary.** The most common mistake is treating them as permanent storage. They should be processed into literature or permanent notes within a day or two, then deleted or archived.

**Permanent notes are written in your own words.** If you're copy-pasting, you're making a literature note, not a permanent one.

---

## Link Types: Choosing the Right Relationship

| Link type | Use when... | Inverse |
|---|---|---|
| `reference` | Simple pointer — "also see this" | `reference` (symmetric) |
| `extends` | This note builds directly on the target | `extended_by` |
| `refines` | This note clarifies or sharpens the target's claim | `refined_by` |
| `contradicts` | Direct tension — these claims conflict | `contradicted_by` |
| `questions` | This note raises a problem for the target | `questioned_by` |
| `supports` | This note provides evidence or reasons for the target | `supported_by` |
| `related` | Thematic connection, no precise direction | `related` (symmetric) |

**Avoid overusing `related`.** It's a last resort for when no directional type fits. A graph full of `related` links conveys no semantic information.

**Always prefer `bidirectional=true`** on `zk_create_link`. Luhmann hand-wrote references on both cards. Bidirectional links make both notes discoverable from either direction.

---

## The Capture → Process → Connect Loop

```
CAPTURE                 PROCESS                CONNECT
  ↓                       ↓                      ↓
Fleeting notes  →   Literature notes   →   Permanent notes
(raw, same day)    (source-anchored)        (own claim, linked)
                                                   ↓
                                          Structure / Hub notes
                                          (topic entry points)
```

**Daily practice:**
1. Process yesterday's fleeting notes (10–15 min)
2. Write 1–3 permanent notes from processed literature
3. Link each permanent note to ≥ 2 existing notes
4. Check health: `zk_health_check`, `zk_get_stats`

---

## Anti-Patterns to Avoid

### The Collector's Fallacy
Saving everything without processing. More saved ≠ more knowledge. Fleeting notes that are never converted don't contribute to the graph.

**Fix:** Process daily. Delete fleeting notes after conversion.

### The Orphan Problem
Creating notes that have no links. They're invisible to future thinking — you'll never encounter them while browsing.

**Fix:** Never create a permanent note without linking it to at least one existing note. Link on creation, not later.

### Over-tagging
Adding 15 tags to compensate for not linking. Tags don't encode *relationships*; they encode categories. A note with 15 tags and no links has categorization, not connectivity.

**Fix:** Use 2–5 focused tags. Prefer links to express "this is related to that."

### Mirror Notes
Notes that paraphrase the source without adding your own thinking. These are literature notes pretending to be permanent notes.

**Fix:** A permanent note must contain your own claim, in your own words. "X says Y" is a literature note. "Y holds because Z" is a permanent note.

### The Archive Trap
Treating structure/hub notes as file folders — placing notes "inside" a topic rather than linking them. Hierarchy defeats the emergence principle.

**Fix:** Structure notes are *entry points*, not containers. Notes live at the flat level; structure notes simply list the most important connections.

### Late Linking
Capturing notes now, planning to add links later. "Later" rarely comes; unlinked notes become permanent orphans.

**Fix:** Link at creation time. If you can't find anything to link right now, search before saving — the inability to link may mean the note is too vague.

---

## ZK + AI Agents: Key Patterns

When an AI agent (Claude, Copilot) works with your Zettelkasten:

### Treat ZK as persistent memory
The database persists across sessions. The agent doesn't remember your previous conversations, but the ZK does. Anchor new work to existing notes.

### Session start protocol
```
1. zk_health_check — find orphans, broken links
2. zk_search_notes(query="[today's topic]") — orient on existing knowledge
3. zk_get_linked_notes on key notes — traverse before creating
```

### Avoid duplicate creation
Search before creating. FTS5 search catches semantic near-duplicates. If a similar permanent note exists, extend it or refine it rather than creating a parallel note.

### Batch link after batch create
When creating multiple notes in one session (e.g., from a research paper), create all notes first, then link them to each other and to older notes. This avoids forward-reference problems.

### Graph density as health metric
`zk_get_stats` shows average links per note. A healthy ZK has:
- **≥ 2.0** average links/note (weak connectivity)
- **≥ 3.0** (good connectivity, emergence becoming possible)
- **< 1.0** (most notes are orphans — linking is being skipped)

---

## Further Reading

- [Taking effective notes: the Zettelkasten method](https://gianmarcodavid.com/posts/zettelkasten/) — Gianmarco David
- [How To Take Smart Notes — Ultimate Guide](https://scrintal.com/guides/how-to-take-smart-notes) — Scrintal
- [Zettelkasten 101](https://www.sloww.co/zettelkasten/) — Sloww (Luhmann strategy + tactics)
- [Niklas Luhmann's Card Index: The Fabrication of Serendipity](https://sociologica.unibo.it/article/view/8350/8272) — Schmidt, *Sociologica*
- [Proper Care for a Digital Zettelkasten](https://www.latematinee.com/p/proper-care-for-a-digital-zettelkasten)
- [A Beginner's Guide to the Zettelkasten Method](https://zenkit.com/en/blog/a-beginners-guide-to-the-zettelkasten-method/) — Zenkit

_Book:_ Sönke Ahrens, *How to Take Smart Notes* (2017) — the canonical modern guide to Luhmann's method.

---

## See Also

- Skill `zettelkasten-mcp` — server setup, operations, issue reporting
