DOCKER_TARGETS=$(filter-out Makefile, $(wildcard *))
DOCKER_ARGS :=

.PHONY: all $(DOCKER_TARGETS) run_perforce

all: $(DOCKER_TARGETS)

$(DOCKER_TARGETS):
	docker build $(DOCKER_ARGS) $@ -t $@

run_perforce:
	cd perforce; docker run -d -e SERVER_NAME=perforce -e P4PASSWD=abcd123efg -p 1667:1666 --name=perforce perforce
