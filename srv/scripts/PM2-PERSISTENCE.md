# Thrive Messenger Server Process Manager

The Thrive Messenger server for `im.tappedin.fm` is managed by PM2 under the `tappedin` account.

- PM2 app name: `thrive-messenger-server`
- App root: `/home/tappedin/apps/ThriveMessenger`
- Start script: `/home/tappedin/apps/ThriveMessenger/srv/scripts/start-thrive-server.sh`
- PM2 config: `/home/tappedin/apps/ThriveMessenger/ecosystem.config.cjs`
- Config loaded by the server: `/home/tappedin/apps/ThriveMessenger/srv/srv.conf`
- Default TCP port: `2005`

Useful commands:

```bash
pm2 status
pm2 logs thrive-messenger-server --lines 100
pm2 restart thrive-messenger-server
pm2 save
pm2 resurrect
```

Persistence:

- PM2 process list is saved with `pm2 save`.
- A tagged user crontab entry runs `pm2 resurrect` on reboot if no user systemd PM2 service is present.
- Do not put SMTP/API passwords in PM2 command arguments or docs. The server reads existing private config files at runtime.
