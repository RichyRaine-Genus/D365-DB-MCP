# Changelog

## [Unreleased]

### Added
- Native `.env` support in the config loader (`db_config.py`). The server now
  loads a `.env` file itself via `python-dotenv`, so standalone / non-VS-Code
  launches work without an external launcher injecting the variables.
  - Precedence: OS environment variables > `.env` > built-in defaults
    (real env vars are never overridden).
  - Search order: explicit `AXDB_DOTENV` path, then the current working
    directory, then the repo root. Missing files are a silent no-op.
- `python-dotenv>=1.0,<2` pinned as a runtime dependency.
