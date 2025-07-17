# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1]

### Fixed

- Bean name and recipe name can be `None`

## [0.5.0]

### Added

- Attached data source to `ProtocolError`

### Fixed

- `ConnectionError` got shadowed by built-in error

### Changed

- Prefixed all Exceptions with `Mahlkoenig`

## [0.4.0]

### Changed

- Wrapped connection errors in custom `ConnectionError`
- Changed `LoginError` to `AuthenticationError`

## [0.3.1]

### Changed

- Relaxed requirement of `pydantic` to `>= 2.10`

## [0.3.0]

### Changed

- Changed `PositiveInt` to `NonNegativeInt` validation to allow for a 0 value
- Raise `ProtocolError` instead of pydantic error

### Fixed

- Use `Grinder` instead of `X54Client` in README example

### Removed

- `print()` statement in receive function

## [0.2.1]

### Changed

- Updated dependencies

## [0.2.0]

No changes. Just a version bump for PyPi

## [0.1.0]

### Added

- Initial commit
