# Changelog

## 2.1.0

### Minor Changes

- 14aac2d: Add Docker image, docker-compose, Docker Hub release workflow, and Changesets versioning
- a378af4: Add optional `search.jsearch_location_suffix` (appended to JSearch queries at collect), expand JSearch country dropdowns, and document onsite/city end-to-end setup with a country-code table.
- 02fcc7c: Add `profiles/onsite_city_example.yaml`: an SF Bay Area onsite/hybrid preset with Remotive/RemoteOK disabled, city keywords, and strict location/work-type flags. Document how to retarget another city.
- bd771aa: Allow profiles to select which job boards run during collect via `search.job_board_sources` (empty = all boards). Onsite/city searches can disable remote-only boards (Remotive, RemoteOK, Arbeitnow).
- 7f7ddd5: Add profile flags `location.strict_location_fit` and `location.strict_work_type` (default off). When enabled, collect and outreach hard-drop location/work-type mismatches instead of only soft-scoring them.

All notable changes to this project will be documented in this file.

The format is managed by [Changesets](https://github.com/changesets/changesets).
