# Design: Analytics & Discovery

## 1. Temporal Queries (`zk_find_notes_in_timerange`) (#13)

**Service layer** — `ZettelService.find_notes_in_timerange`

```python
def find_notes_in_timerange(
    self,
    start_date: str,
    end_date: str,
    date_field: str = "created_at",
    include_linked: bool = False,
    note_type: Optional[str] = None,
) -> dict:
```

**Repository layer** — SQL query using SQLAlchemy:

```python
col = DBNote.created_at if date_field == "created_at" else DBNote.updated_at
stmt = (
    select(DBNote)
    .where(col >= start_dt, col <= end_dt)
    .options(joinedload(DBNote.tags), joinedload(DBNote.outgoing_links))
)
```

If `include_linked=True`, a second query fetches all notes linked from the
primary result set (one extra `IN` clause, no recursion).

Date parsing validates ISO 8601 format with `datetime.fromisoformat`; raises
`ValueError` on failure.

**Index**: `DBNote.created_at` and `DBNote.updated_at` should be indexed
in SQLAlchemy model — add `Index('ix_notes_created_at', DBNote.created_at)` and
`Index('ix_notes_updated_at', DBNote.updated_at)` in `db_models.py`.

---

## 2. Tag Co-occurrence Analysis (`zk_analyze_tag_clusters`) (#15)

**Algorithm** — pure SQL, no external libs:

```sql
SELECT a.tag_id AS tag_a, b.tag_id AS tag_b, COUNT(*) AS co_count
FROM note_tags a
JOIN note_tags b ON a.note_id = b.note_id AND a.tag_id < b.tag_id
GROUP BY a.tag_id, b.tag_id
HAVING co_count >= :min_co_occurrence
ORDER BY co_count DESC
```

Post-processing in Python groups overlapping pairs into clusters using union-find
(no external graph library required). Each cluster collects up to 5
representative note IDs from the most co-occurring pair.

**Service layer** — `SearchService.analyze_tag_clusters(min_co_occurrence: int)`

Returns:
```json
{
  "clusters": [
    {
      "tags": ["ai-agents", "agentic-programming"],
      "count": 47,
      "representative_notes": ["20260130T...", ...]
    }
  ],
  "total_tag_pairs_analysed": 1240
}
```

**Performance note**: The SQL join is O(N²) on `note_tags` rows. For 10 000
notes × avg 3 tags = 30 000 rows, the self-join produces ~450 M pairs before
filtering, which is too slow. We instead limit the join with a
`LIMIT 1000` on the inner tag sub-query ordered by note count, covering the
top-1000 most-used tags only — sufficient for the 95% use case.
