# Design: Advanced Features

## 1. Flexible/Custom Link Types (#10)

**Storage**: New `LinkTypeRegistry` class in `models/schema.py`.
Custom types are persisted in `openspec/config.yaml` under a `custom_link_types`
key so they are version-controlled with the project.

```python
class LinkTypeRegistry:
    BUILT_IN: dict[str, LinkTypeDef] = { ... }   # existing 7 types
    _custom: dict[str, LinkTypeDef] = {}

    def register(self, name, inverse, symmetric): ...
    def is_valid(self, name) -> bool: ...
    def get_inverse(self, name) -> str: ...
```

`NoteRepository` replaces the hardcoded `LinkType` enum check with
`LinkTypeRegistry.is_valid()`.

`zk_register_link_type` persists to `openspec/config.yaml` and calls
`LinkTypeRegistry.register()`.

---

## 2. Link Type Inference (#11)

**Algorithm**: keyword-pattern matching (no ML dependency).

- Extract noun phrases from both notes using simple regex / stopword removal
- Score each built-in link type against a pattern dictionary:
  - `extends`: source has "building on", "expanding", target has definitions
  - `supports`: source has "evidence", "demonstrates", "confirms"
  - `contradicts`: source/target contain opposing stance keywords
- Return top-3 scores normalised to [0, 1]

Implemented in a new `services/inference_service.py` module.

---

## 3. Auto-Tagging Suggestions (#12)

**Algorithm**: TF-IDF cosine similarity (pure Python, no external ML).

- Pre-compute a term-frequency vector per tag from all notes carrying that tag
- On query, tokenise the new content and compute cosine similarity vs. each tag vector
- Return top-10 tags sorted by score

Cached in memory; cache invalidated on `zk_rebuild_index`.
Implemented in `services/search_service.py` (extend existing class).

---

## 4. Graceful Degradation (#16)

**Pattern**: try/except in `NoteRepository` with fallback to
`_read_from_markdown(note_id)`.

```python
def get(self, note_id: str) -> Optional[Note]:
    try:
        return self._get_from_db(note_id)
    except Exception as e:
        logger.warning(f"DB unavailable, falling back to filesystem: {e}")
        return self._read_from_markdown(note_id)
```

Write operations log a warning but still write the Markdown file; they append
to a `data/pending_index.txt` queue for the next successful rebuild.

---

## 5. Self-Healing Index (#17)

**On server startup** (in `main.py`):

```python
fs_count  = len(list(notes_dir.glob("*.md")))
db_count  = session.execute(count(DBNote.id)).scalar()
drift_pct = abs(fs_count - db_count) / max(fs_count, 1) * 100

if config.auto_rebuild_threshold > 0 and drift_pct > config.auto_rebuild_threshold:
    logger.info(f"Auto-rebuild: {drift_pct:.1f}% drift ({db_count}/{fs_count})")
    repository.rebuild_index()
elif drift_pct > 0:
    logger.warning(f"Index drift {drift_pct:.1f}% — run zk_rebuild_index")
```

New config key: `ZETTELKASTEN_AUTO_REBUILD_THRESHOLD` (default: `5`, int percent;
`0` = disabled).
