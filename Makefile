.PHONY: raspi-client-test server-setup server-run server-test server-up server-stop local-client-setup local-client-run local-client-record local-client-test local-client-up local-client-stop raspi-client-setup raspi-client-run replay collect raspi-client-up raspi-client-stop raspi-client-restart raspi-client-logs replay-start replay-stop replay-restart replay-logs

export PATH := $(or $(CARGO_HOME),$(HOME)/.cargo)/bin:$(HOME)/.local/bin:$(PATH)
CARGO ?= cargo

.PHONY: rust-setup
rust-setup:
	sudo apt update
	sudo apt install -y cmake libsdl3-dev
	@set -eu; \
	if ! command -v rustup >/dev/null 2>&1; then \
		installer=$$(mktemp); \
		trap 'rm -f "$$installer"' EXIT HUP INT TERM; \
		curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o "$$installer"; \
		sh "$$installer" -y --profile minimal --default-toolchain stable; \
	fi; \
	rustup toolchain install stable --profile minimal --component rustfmt --component clippy; \
	rustup default stable; \
	rustc --version; \
	$(CARGO) --version

server-setup:
	cmake -S server/native -B server/native/build -DCMAKE_BUILD_TYPE=Release
	cmake --build server/native/build --target lenia --parallel 2
	cd server && $(CARGO) build --release --locked

server-run:
	cd server && ./target/release/server

server-test:
	cd server && $(CARGO) test --release --locked

server-up:
	cd server && pm2 start ecosystem.config.js --only server
	pm2 save

server-stop:
	pm2 stop server
	pm2 save

local-client-setup:
	cd local_client && $(CARGO) build --release --locked

local-client-run:
	cd local_client && ./target/release/local-client

local-client-record:
	cd local_client && ./target/release/local-client --record animation.mp4

local-client-test:
	cd local_client && $(CARGO) test --release --locked
	$(CARGO) test --manifest-path client_core/Cargo.toml --release --locked

local-client-up:
	cd local_client && pm2 start ecosystem.config.js --only local-client
	pm2 save

local-client-stop:
	pm2 stop local-client
	pm2 save

raspi-client-test:
	cd raspi_client && $(CARGO) test --release --locked

raspi-client-setup:
	cd raspi_client && $(CARGO) build --release --locked

raspi-client-run:
	cd raspi_client && ./target/release/raspi-client

replay:
	cd raspi_client && ./target/release/raspi-client replay

collect:
	cd raspi_client && ./target/release/raspi-client collect

raspi-client-up:
	cd raspi_client && pm2 start ecosystem.config.js --only lenia-client
	pm2 save

raspi-client-stop:
	pm2 stop lenia-client
	pm2 save

raspi-client-restart:
	cd raspi_client && pm2 restart ecosystem.config.js --only lenia-client --update-env
	pm2 save

raspi-client-logs:
	pm2 logs lenia-client

replay-start:
	cd raspi_client && pm2 start ecosystem.config.js --only lenia-replay
	pm2 save

replay-stop:
	pm2 stop lenia-replay
	pm2 save

replay-restart:
	cd raspi_client && pm2 restart ecosystem.config.js --only lenia-replay --update-env
	pm2 save

replay-logs:
	pm2 logs lenia-replay

raspi-client-run replay collect raspi-client-up raspi-client-restart replay-start replay-restart: export XDG_RUNTIME_DIR ?= /run/user/$(shell id -u)
raspi-client-run replay collect raspi-client-up raspi-client-restart replay-start replay-restart: export WAYLAND_DISPLAY ?= wayland-0
raspi-client-run replay collect raspi-client-up raspi-client-restart replay-start replay-restart: export SDL_VIDEO_DRIVER := wayland
