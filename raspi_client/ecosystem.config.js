const path = require("path")

module.exports = {
    apps: [
        {
            name: "lenia-client",
            cwd: __dirname,
            script: path.join(__dirname, "target/release/raspi-client"),
            args: [],
            interpreter: "none",
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
            env: {
                XDG_RUNTIME_DIR: process.env.XDG_RUNTIME_DIR || `/run/user/${process.getuid()}`,
                WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY || "wayland-0",
                SDL_VIDEO_DRIVER: "wayland",
            },
        },
        {
            name: "lenia-replay",
            cwd: __dirname,
            script: path.join(__dirname, "target/release/raspi-client"),
            args: ["replay"],
            interpreter: "none",
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
            env: {
                XDG_RUNTIME_DIR: process.env.XDG_RUNTIME_DIR || `/run/user/${process.getuid()}`,
                WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY || "wayland-0",
                SDL_VIDEO_DRIVER: "wayland",
            },
        },
    ],
}
