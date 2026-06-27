If your implementation adds, removes, or renames storage structures (database tables, columns, storage keys, or data format):

1. Bump the schema version in the appropriate version constant.
2. Add an upgrade handler for each version step (old version → new version).
3. Write a migration test:
   - Open a store at the previous schema version (recreate the old structure manually).
   - Re-open with the new version so the upgrade handler runs.
   - Assert the new structure exists and existing data is preserved.
4. Never apply destructive changes (dropping a column or table that contains user data) without explicit user approval — stop and ask first.

**No migration needed for:** in-memory state, computed/derived fields, nullable columns with no existing rows, configuration-only changes with no stored data impact.
