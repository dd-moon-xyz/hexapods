const path = require("path")

module.exports = {
    apps: [
        {
            name: "server",
            cwd: __dirname,
            script: path.join(__dirname, "target/release/server"),
            args: ["--bind", process.env.SERVER_BIND || "0.0.0.0:9877"],
            interpreter: "none",
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
        },
    ],
}
