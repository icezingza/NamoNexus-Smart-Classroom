# Recovery Notes

## Situation

The original workspace content could not be recovered from this folder after an unintended deletion during cleanup.

## Rebuilt from surviving information

- Backend package name: `namo_core`
- Frontend package name: `dashboard`
- Previously observed package metadata and dependency choices
- Surviving roadmap and architecture documents found in `D:\Users\NAMO_CORE_MASTER`

## Recreated in this recovery

- Clean directory structure
- Minimal backend endpoints for health, status, knowledge search, classroom session, lessons, and devices
- Demo engine, device, module, and service layers matching more of the earlier observed layout
- Minimal React dashboard that talks to the backend
- Sample knowledge files so the search flow works
- Local backup script for future cleanup safety
- Repo hygiene via root `.gitignore`

## Still missing

- Original implementation details
- Original tests beyond the recreated smoke tests
- Original `roadmap` assets such as `.docx`, `.sql`, and milestone snapshots
- Original zip archives and ad hoc scripts

## Recommended next steps

1. Restore any external backup, cloud sync copy, or another clone if one exists.
2. Compare that source against this rebuilt starter and merge the real code back in.
3. Reinitialize git only after the recovered source is in a known-good state.
4. Add automated backups before another cleanup pass.
