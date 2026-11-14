.PHONY: raspi-client-test server-setup server-run server-test server-up server-stop local-client-setup local-client-run local-client-test local-client-up local-client-stop raspi-client-setup raspi-client-run raspi-client-up raspi-client-stop raspi-client-restart raspi-client-logs
.PHONY: fallback-record fallback-download fallback-publish

fallback-download:
	python3 scripts/fallback_asset.py download

fallback-publish:
	uv run --locked --directory client/local python ../../scripts/fallback_asset.py publish

fallback-record:
	python3 scripts/connection.py run local uv run --locked python ../../scripts/bundle_fallback.py

export PATH := $(or $(CARGO_HOME),$(HOME)/.cargo)/bin:$(HOME)/.local/bin:$(PATH)
CARGO ?= cargo

.PHONY: server-restart local-client-restart

server-restart:
	python3 scripts/connection.py run server pm2 restart ecosystem.config.js --only server --update-env
	pm2 save

local-client-restart:
	pm2 stop local-client
	python3 scripts/connection.py run local pm2 restart ecosystem.config.js --only local-client --update-env
	pm2 save

.PHONY: rust-setup
rust-setup:
	sudo apt update
	sudo apt install -y cmake
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
	cmake --build server/native/build --target hexapods --parallel 2
	cd server && $(CARGO) build --release --locked

server-run:
	python3 scripts/connection.py run server ./target/release/server

server-test:
	cd server && $(CARGO) test --release --locked

server-up:
	python3 scripts/connection.py run server pm2 start ecosystem.config.js --only server
	pm2 save

server-stop:
	pm2 stop server
	pm2 save

local-client-setup: fallback-download
	cd client/local && uv sync --locked

local-client-run:
	python3 scripts/connection.py run local uv run --locked local-client

local-client-test: fallback-download
	cd client/local && uv run --locked pytest -n auto ../core/tests

local-client-up:
	python3 scripts/connection.py run local pm2 start ecosystem.config.js --only local-client
	pm2 save

local-client-stop:
	pm2 stop local-client
	pm2 save

raspi-client-test:
	cd client/raspi && uv run --locked pytest -n auto tests

raspi-client-setup: fallback-download
	cd client/raspi && uv sync --locked

raspi-client-run:
	python3 scripts/connection.py run raspi uv run --locked hexapods-client

raspi-client-up:
	python3 scripts/connection.py run raspi pm2 start ecosystem.config.js --only hexapods-client
	pm2 save

raspi-client-stop:
	pm2 stop hexapods-client
	pm2 save

raspi-client-restart:
	pm2 stop hexapods-client
	python3 scripts/connection.py run raspi pm2 restart ecosystem.config.js --only hexapods-client --update-env
	pm2 save

raspi-client-logs:
	pm2 logs hexapods-client

raspi-client-run raspi-client-up raspi-client-restart: export XDG_RUNTIME_DIR ?= /run/user/$(shell id -u)
raspi-client-run raspi-client-up raspi-client-restart: export WAYLAND_DISPLAY ?= wayland-0
raspi-client-run raspi-client-up raspi-client-restart: export SDL_VIDEODRIVER := wayland
