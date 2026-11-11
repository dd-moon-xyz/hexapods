const path = require("path")

module.exports = {
    apps: [
        {
            name: "server",
            cwd: __dirname,
            script: path.join(__dirname, "target/release/server"),
            interpreter: "none",
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
        },
    ],
}
