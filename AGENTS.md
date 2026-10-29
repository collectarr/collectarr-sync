# Working rules

- Follow the user's instructions over this file.
- Use conventional commit titles. For real changes, add a body: what changed,
  why, and how it was checked. Do not use one-line commits for whole stages.
- No legacy support, compatibility layers, deprecated aliases or dead code.
- After the initial Music baseline, change schemas with explicit ordered
  migrations. Never reset a database to make an upgrade work.
- Never modify live databases or backups. Use isolated test storage.
- Do not rewrite history or replace published tags without an explicit request.
- CLZ is a reference only. Do not copy its code, paid fonts or proprietary assets.
- Sync personal library data. Core owns canonical catalog data.

- Follow docs/release-notes.md for release descriptions. Write the editorial summary in docs/release-summaries.json; generate What's Changed with tool/release_notes.py. Keep contributor credit and comparison links.
