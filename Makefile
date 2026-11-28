# Override on the command line, e.g. `make install PIXOO_IP=192.168.1.60`
REPO     := $(CURDIR)
PIXOO_IP ?= 192.168.1.50
RA_USER  ?= kelsin
LB_USER  ?= kelsin13
BGG_USER ?= Kelsin

LABEL := com.retro-pixoo.hourly
PLIST := $(HOME)/Library/LaunchAgents/$(LABEL).plist
EXPORT_LABEL := com.retro-pixoo.lb-export
EXPORT_PLIST := $(HOME)/Library/LaunchAgents/$(EXPORT_LABEL).plist
LOG   := $(HOME)/Library/Logs/retro-pixoo.log
GUI   := gui/$(shell id -u)

.DEFAULT_GOAL := help
.PHONY: help sync test preview update keychain-ra keychain-bgg plist install \
        uninstall reload run export status logs

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

sync: ## Install dependencies into .venv
	uv sync

test: ## Run the test suite
	uv run pytest

preview: ## Render every page from sample data into preview/ (no network or device)
	uv run retro-pixoo-update --sample --preview preview

update: ## Fetch live data and push to the Pixoo (needs RA_API_KEY, PIXOO_IP)
	uv run retro-pixoo-update

keychain-ra: ## Store the RetroAchievements API key in the login Keychain (prompts)
	security add-generic-password -s retro_pixoo -a "$$USER" -w

keychain-bgg: ## Store the BGG token in the login Keychain (prompts)
	security add-generic-password -s retro_pixoo_bgg -a "$$USER" -w

plist: ## Write the hourly and weekly-export launchd agent plists (uses REPO, PIXOO_IP, *_USER)
	@mkdir -p $(dir $(PLIST))
	sed -e 's|@LABEL@|$(LABEL)|g' -e 's|@REPO@|$(REPO)|g' -e 's|@PIXOO_IP@|$(PIXOO_IP)|g' \
	    -e 's|@RA_USER@|$(RA_USER)|g' -e 's|@LB_USER@|$(LB_USER)|g' \
	    -e 's|@BGG_USER@|$(BGG_USER)|g' -e 's|@LOG@|$(LOG)|g' \
	    launchd/$(LABEL).plist.in > $(PLIST)
	plutil -lint $(PLIST)
	sed -e 's|@EXPORT_LABEL@|$(EXPORT_LABEL)|g' -e 's|@LOG@|$(LOG)|g' \
	    launchd/$(EXPORT_LABEL).plist.in > $(EXPORT_PLIST)
	plutil -lint $(EXPORT_PLIST)

install: sync plist ## Sync deps, write the plists and load them (hourly update runs once now)
	launchctl bootstrap $(GUI) $(PLIST)
	launchctl bootstrap $(GUI) $(EXPORT_PLIST)

uninstall: ## Stop and unload both agents, delete their plists
	-launchctl bootout $(GUI)/$(LABEL)
	-launchctl bootout $(GUI)/$(EXPORT_LABEL)
	rm -f $(PLIST) $(EXPORT_PLIST)

reload: ## Rewrite the plists and reload both agents (after changing settings)
	-launchctl bootout $(GUI)/$(LABEL)
	-launchctl bootout $(GUI)/$(EXPORT_LABEL)
	$(MAKE) plist
	launchctl bootstrap $(GUI) $(PLIST)
	launchctl bootstrap $(GUI) $(EXPORT_PLIST)

run: ## Run the agent now
	launchctl kickstart -k $(GUI)/$(LABEL)

export: ## Download a Letterboxd export now (opens the browser)
	open https://letterboxd.com/data/export/

status: ## Show agent status and last exit code
	launchctl print $(GUI)/$(LABEL)

logs: ## Tail the agent log
	tail -f $(LOG)
