---
description: Standard workflow for committing, pushing to GitHub, and deploying to Streamlit
globs: ["**/*"]
---

# GitHub & Streamlit Deployment Workflow

1. **Automatic Sync & Deployment**:
   - Unless the user explicitly instructs to keep changes local (e.g. "don't push"), always ensure verified changes are committed with clear semantic commit messages and pushed to `origin/main`.
   - Pushing to `origin/main` automatically syncs the live deployment on Streamlit Community Cloud.

2. **Commit & Push Procedure**:
   - Verify changes with clean syntax / imports first.
   - Stage relevant modified files (`git add <files>`).
   - Commit with a descriptive message (`git commit -m "..."`).
   - Push to remote (`git push origin main`).

3. **Explicit Override Respect**:
   - If the user specifically instructs "don't push" or "keep it local", retain changes in the working tree without running `git push`.
