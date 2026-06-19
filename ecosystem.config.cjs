module.exports = {
  apps: [
    {
      name: 'thrive-messenger-server',
      cwd: '/home/tappedin/apps/ThriveMessenger',
      script: '/home/tappedin/apps/ThriveMessenger/srv/scripts/start-thrive-server.sh',
      interpreter: 'bash',
      autorestart: true,
      max_restarts: 20,
      restart_delay: 5000,
      watch: false,
      time: true,
      env: {
        NODE_ENV: 'production'
      }
    }
  ]
};
