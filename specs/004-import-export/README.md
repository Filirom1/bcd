# ❌ SPEC 004: Import/Export - ABANDONED

**Status**: ABANDONED (2026-02-06)
**Reason**: Over-engineered solution

This specification was abandoned during the planning phase due to excessive complexity.

## What Happened

- **Original goal**: CSV import/export with BCDI/Dublin Core compatibility
- **Complexity creep**: Added configurable medium type taxonomy, multilingual support, fuzzy normalization, admin UI
- **Result**: 2000+ lines of spec, 17 new files, 3 new database tables, 40+ hours implementation
- **Reality check**: User asked "why not just store medium types as plain text like titles?"

## See Details

Read [ABANDONED.md](./ABANDONED.md) for full explanation and the simpler alternative approach.

## Next Steps

Create a new, simplified spec that:
- ✅ Imports CSV files (BCDI, Dublin Core, etc.)
- ✅ Exports CSV files (Standard, BCDI, Dublin Core)
- ✅ Stores medium types as plain text (no normalization)
- ✅ Filters using standard search (no lookup tables)
- ❌ NO configurable taxonomy
- ❌ NO multilingual mapping
- ❌ NO admin configuration UI

**Estimated effort reduction**: 40 hours → 15-20 hours

---

**Lesson**: Simple solutions beat complex ones. Start with the simplest thing that could work.
