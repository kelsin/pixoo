# Override on the command line, e.g. `make install PIXOO_IP=192.168.1.60`
REPO     := $(CURDIR)
PIXOO_IP ?= 192.168.1.50
RA_USER  ?= kelsin
LB_USER  ?= kelsin13
BGG_USER ?= Kelsin

LABEL := com.retro-pixoo.hourly
PLIST := $(HOME)/Library/LaunchAgents/$(LABEL).plist
# Removed weekly export agent; uninstall/reload still clean it up
LEGACY_LABEL := com.retro-pixoo.lb-export
LEGACY_PLIST := $(HOME)/Library/LaunchAgents/$(LEGACY_LABEL).plist
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

plist: ## Write the hourly launchd agent plist (uses REPO, PIXOO_IP, *_USER)
	@mkdir -p $(dir $(PLIST))
	sed -e 's|@LABEL@|$(LABEL)|g' -e 's|@REPO@|$(REPO)|g' -e 's|@PIXOO_IP@|$(PIXOO_IP)|g' \
	    -e 's|@RA_USER@|$(RA_USER)|g' -e 's|@LB_USER@|$(LB_USER)|g' \
	    -e 's|@BGG_USER@|$(BGG_USER)|g' -e 's|@LOG@|$(LOG)|g' \
	    launchd/$(LABEL).plist.in > $(PLIST)
	plutil -lint $(PLIST)

install: sync plist ## Sync deps, write the plist and load it (hourly update runs once now)
	launchctl bootstrap $(GUI) $(PLIST)

uninstall: ## Stop and unload the agent, delete its plist
	-launchctl bootout $(GUI)/$(LABEL)
	-launchctl bootout $(GUI)/$(LEGACY_LABEL)
	rm -f $(PLIST) $(LEGACY_PLIST)

reload: ## Rewrite the plist and reload the agent (after changing settings)
	-launchctl bootout $(GUI)/$(LABEL)
	-launchctl bootout $(GUI)/$(LEGACY_LABEL)
	rm -f $(LEGACY_PLIST)
	$(MAKE) plist
	launchctl bootstrap $(GUI) $(PLIST)

run: ## Run the agent now
	launchctl kickstart -k $(GUI)/$(LABEL)

export: ## Download a Letterboxd export now (opens the browser)
	open https://letterboxd.com/data/export/

status: ## Show agent status and last exit code
	launchctl print $(GUI)/$(LABEL)

logs: ## Tail the agent log
	tail -f $(LOG)
