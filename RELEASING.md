# Releasing and server updates

- **Release branch:** `integration/account-management-live`. What is on this branch on Gitea is what the production servers run.
- **Servers:** the Thrive server (im.tappedin.fm), restarted through thrive-safe-restart when chat is quiet. They update themselves: `release-deploy.timer` on server.devine-creations.com checks every
  15 minutes and deploys a new pushed commit when the servers are idle, with a backup, a health check and automatic
  rollback. It never deploys a commit that doesn't contain the live one, and it refuses (and alerts) if a server has
  edits that are in no pushed commit.
- **Rule for everyone (agents included):** every live fix is committed and pushed (Gitea + GitHub mirror) the same
  day; deploy only from pushed commits; all servers of the product run the same version. Never hot-edit a server.
- **Pause while you work:** `echo "reason, who, until" > /home/devinecr/jobs/.deploy-hold/thrive`; delete it to resume.
- **Check:** `sudo release-deploy thrive --check`. Results and failures: `app-health failures --app servers`.
- Full docs: Gitea Raywonder/server-ops, `release-sync/README.md`.
