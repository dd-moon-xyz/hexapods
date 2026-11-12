const path = require("path")

module.exports = {
    apps: [
        {
            name: "local-client",
            cwd: __dirname,
            script: path.join(__dirname, ".venv/bin/local-client"),
            interpreter: "none",
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
        },
    ],
}
