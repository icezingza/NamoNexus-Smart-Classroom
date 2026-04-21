# Scripts

`backup_project.ps1` creates a zip backup of the reconstructed source and docs
without relying on `node_modules`, build artifacts, or local virtual environments.

Run from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup_project.ps1
```
