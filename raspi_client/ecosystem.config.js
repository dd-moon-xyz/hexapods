const path = require("path")
const os = require("os")

module.exports = {
    apps: [
        {
            name: "lenia-client",
            cwd: __dirname,
            script: path.join(os.homedir(), ".local/bin/uv"),
            args: ["run", "--no-sync", "lenia-client"],
            interpreter: "none",
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
            env: {
                XDG_RUNTIME_DIR: process.env.XDG_RUNTIME_DIR || `/run/user/${process.getuid()}`,
                WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY || "wayland-0",
                SDL_VIDEODRIVER: "wayland",
                PYTHONUNBUFFERED: "1",
            },
        },
        {
            name: "lenia-replay",
            cwd: __dirname,
            script: path.join(os.homedir(), ".local/bin/uv"),
            args: ["run", "--no-sync", "lenia-replay"],
            interpreter: "none",
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
            env: {
                XDG_RUNTIME_DIR: process.env.XDG_RUNTIME_DIR || `/run/user/${process.getuid()}`,
                WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY || "wayland-0",
                SDL_VIDEODRIVER: "wayland",
                PYTHONUNBUFFERED: "1",
            },
        },
    ],
}
