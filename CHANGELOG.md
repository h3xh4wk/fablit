# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **SPEC-005 — Assessment Activity Domain Foundation**: in-memory `Assessment` and `AssessmentActivity` domain models under `fablit.domain`.
  - Stable unique identities, metadata, lifecycle status, and controlled activity types.
  - Domain validation enforcing identity, required metadata, minimum activity count, and deterministic sequential activity ordering.
  - Domain exceptions: `InvalidAssessmentError`, `InvalidActivityError`, `DuplicateActivityPositionError`.
  - Unit, composition, and domain-independence tests (100% coverage for `fablit.domain`).
  - Documentation updates to the Domain Language, Architecture Blueprint, and README.

See [SPEC-005](specifications/platform/SPEC-005-assessment-activity-domain-foundation.md) for details.
