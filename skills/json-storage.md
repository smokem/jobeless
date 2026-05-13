# Skill: JSON Storage

## Purpose
Manage all application state locally using schema-validated JSON files with atomic write operations.

## Key Libraries
- `pathlib`: For robust cross-platform path management
- `pydantic`: For schema validation and serialization
- `shutil`: For atomic file renaming

## Implementation Pattern
1. **Atomic Writes**:
   - Write new data to a `.tmp` file first.
   - Use `os.replace()` to overwrite the target file with the temp file.
   - This prevents data corruption during system crashes.
2. **Schema Validation**:
   - Every read must be parsed through a Pydantic model.
   - If validation fails, log the error and raise an exception (never use corrupted data).
3. **Directory Structure**:
   - Resolved from `config.py → DATA_DIR`.
   - `data/profile.json`: User master profile.
   - `data/targets.json`: Discovery session results.
   - `data/history.json`: Cumulative application history.
   - `data/applications/{company_id}/`: Per-company artifact storage.
4. **Archive Pattern**:
   - NEVER delete data unless explicitly requested.
   - Mark records with `archived: true` and filter them out of the active UI view.

## Known Pitfalls
- **Race Conditions**: Since this is a single-user local app, race conditions are rare, but always close file handles immediately after reading/writing.
- **Large Files**: If `history.json` grows > 10MB, implement pagination or split by year (e.g., `history_2026.json`).
- **Path Issues**: Always use `Path` from `pathlib` to avoid backslash/forward-slash issues on Windows vs. Linux.

## Test Approach
- Verify atomic write by interrupting a write process and checking file integrity.
- Run schema validation tests with missing or malformed JSON keys.
- Ensure all paths are resolved relative to the project root.
