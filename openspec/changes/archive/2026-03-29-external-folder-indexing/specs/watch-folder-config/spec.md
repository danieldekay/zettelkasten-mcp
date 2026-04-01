## ADDED Requirements

### Requirement: Watch directories are configurable via environment variable
The system SHALL read `ZETTELKASTEN_WATCH_DIRS` from the environment as a comma-separated list of absolute directory paths. Each path SHALL be validated to exist and be a directory. Invalid paths SHALL produce a startup warning log entry and be skipped rather than causing a fatal error. An unset or empty `ZETTELKASTEN_WATCH_DIRS` SHALL result in an empty watch-dirs list (feature disabled). The parsed list of valid `Path` objects SHALL be stored on `ZettelkastenConfig` as `watch_dirs: list[Path]`.

#### Scenario: Single valid watch directory
- **WHEN** `ZETTELKASTEN_WATCH_DIRS` is set to `/home/user/docs`
- **THEN** `ZettelkastenConfig.watch_dirs` contains exactly one entry: `Path("/home/user/docs")`

#### Scenario: Multiple valid watch directories
- **WHEN** `ZETTELKASTEN_WATCH_DIRS` is set to `/home/user/docs,/home/user/books`
- **THEN** `ZettelkastenConfig.watch_dirs` contains exactly two entries

#### Scenario: Non-existent path is skipped with a warning
- **WHEN** `ZETTELKASTEN_WATCH_DIRS` contains a path that does not exist on disk
- **THEN** the server starts successfully
- **AND** a WARNING log entry is emitted naming the invalid path
- **AND** `ZettelkastenConfig.watch_dirs` does not contain that path

#### Scenario: Unset env var disables feature
- **WHEN** `ZETTELKASTEN_WATCH_DIRS` is not set
- **THEN** `ZettelkastenConfig.watch_dirs` is an empty list
- **AND** no watch-folder indexing is performed at startup
