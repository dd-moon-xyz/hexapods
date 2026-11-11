.PHONY: local-client-run local-client-up local-client-stop raspi-client-run raspi-client-up server-run local-client-setup local-client local-client-record raspi-client-setup raspi-client raspi-client-start raspi-client-stop raspi-client-restart raspi-client-logs gif video desktop-client desktop-client-record core-build core-run devcontainer-build app-build app-run app-up app-stop app-restart client-setup client replay collect client-start client-stop client-restart client-logs replay-start replay-stop replay-restart replay-logs server-build server-up server-stop

export PATH := $(HOME)/.local/bin:$(PATH)


gif:
	cd server && uv run python -m lenia.scripts.record_hexapod_cuda

video:
	cd server && uv run python -m lenia.scripts.record_hexapod_cuda --output resources/hexapod/propulsion.mp4 --speed 5 --story

local-client-setup:
	cd local_client && uv sync

local-client-run:
	cd local_client && uv run local-client

local-client-up:
	cd local_client && pm2 start ecosystem.config.js --only local-client
	pm2 save

local-client-stop:
	pm2 stop local-client
	pm2 save

local-client: local-client-run

local-client-record:
	cd local_client && uv run local-client --record animation.mp4

desktop-client: local-client

desktop-client-record: local-client-record

core-build:
	cd server && docker compose build lenia-core

core-run:
	cd server && docker compose run --rm lenia-core

devcontainer-build:
	cd server && docker compose build lenia-devcontainer

app-build:
	cd server && docker compose build lenia-app

app-run:
	cd server && docker compose run --rm --service-ports lenia-app

app-up:
	cd server && docker compose up -d lenia-app

app-stop:
	cd server && docker compose stop lenia-app

app-restart: app-stop app-up

raspi-client-setup:
	cd raspi_client && uv sync

raspi-client-run:
	cd raspi_client && uv run lenia-client

raspi-client: raspi-client-run

raspi-client-up: raspi-client-start

replay:
	cd raspi_client && uv run lenia-replay

collect:
	cd raspi_client && uv run lenia-collect

raspi-client-start:
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

server-build: app-build

server-up: app-up

server-run: app-run

server-stop: app-stop

raspi-client-run replay collect raspi-client-start raspi-client-restart replay-start replay-restart: export XDG_RUNTIME_DIR ?= /run/user/$(shell id -u)
raspi-client-run replay collect raspi-client-start raspi-client-restart replay-start replay-restart: export WAYLAND_DISPLAY ?= wayland-0
raspi-client-run replay collect raspi-client-start raspi-client-restart replay-start replay-restart: export SDL_VIDEODRIVER := wayland

client-setup: raspi-client-setup

client: raspi-client

client-start: raspi-client-start

client-stop: raspi-client-stop

client-restart: raspi-client-restart

client-logs: raspi-client-logs
