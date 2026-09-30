# Deep Testing Report: AI Models & Video Rendering Components

## Environment Setup Issues
1. **Missing Test Dependencies**: The `backend` environment is missing crucial testing dependencies right out of the box (`greenlet`, `asyncpg`, `python-jose`, and `pydantic[email]`). These must be manually installed or explicitly defined in the test dependencies section.
2. **PostgreSQL Dependency**: End-to-end (E2E) tests for Phase 3 and Phase 4 fail instantly with `ConnectionRefusedError: [WinError 1225]` because they expect a running PostgreSQL instance accessible via `asyncpg`.
3. **Windows Encoding Bug**: The E2E test scripts (`test_phase3_e2e.py` and `test_phase4_e2e.py`) contain Unicode checkmarks (`✓` and `❌`). Running these on standard Windows terminals causes a `UnicodeEncodeError`. Setting `PYTHONIOENCODING=utf-8` works around it.
4. **PYTHONPATH Issues**: Top-level modules like `video_engine` are not automatically discoverable when running tests from within the backend directory. `PYTHONPATH` needs to be explicitly set to the repository root.

## Bugs Discovered

1. **`passlib` / `bcrypt` Version Incompatibility**: 
   - **Symptom**: `ValueError: password cannot be longer than 72 bytes, truncate manually if necessary`.
   - **Cause**: The application is using `passlib` with `bcrypt >= 4.0.0`. Newer versions of `bcrypt` changed their expected input format, breaking `passlib`'s hashing mechanism when creating users.
   - **Fix**: Either downgrade `bcrypt` to `< 4.0.0` or replace `passlib` with a direct `bcrypt` implementation in `app.core.security`.

2. **Missing Fixtures in Rendering Tests**:
   - **Symptom**: Running `pytest backend/tests/test_rendering.py` fails during setup with `fixture 'client' not found` and `fixture 'auth_headers' not found`.
   - **Cause**: There is no `conftest.py` in the `backend/tests` directory. The rendering tests rely on fixtures defined locally inside `test_api.py`, making `test_rendering.py` unrunnable on its own.
   - **Fix**: Extract the database, client, and authentication fixtures from `test_api.py` into a shared `conftest.py`.

## Component Testing (AI Models & Rendering)
- **Phase 3 (Media Analysis)**: E2E test verifies shot detection, keyframe extraction, scene detection, audio analysis, and speech transcription using FFmpeg mock videos. Fails due to the DB connection.
- **Phase 4 (AI Director)**: E2E test verifies story candidate generation, timeline assembly, and knowledge graph construction. Fails due to the DB connection.
- **Video Rendering (`test_rendering.py`)**: Tests endpoints for listing presets, previewing renders, checking job status, canceling jobs, and exporting renders. Un-testable directly due to the missing fixtures bug mentioned above.

*All findings have been logged for review.*
