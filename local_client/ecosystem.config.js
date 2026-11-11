const path = require("path")
const os = require("os")

module.exports = {
    apps: [
        {
            name: "local-client",
            cwd: __dirname,
            script: path.join(os.homedir(), ".local/bin/uv"),
            args: ["run", "--no-sync", "local-client"],
            interpreter: "none",
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
            env: {
                PYTHONUNBUFFERED: "1",
            },
        },
    ],
}
