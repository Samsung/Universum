DOCKER_TARGETS=$(filter-out Makefile, $(wildcard *))

.PHONY: all $(DOCKER_TARGETS) run_perforce

all: $(DOCKER_TARGETS)

$(DOCKER_TARGETS):
	docker build $@ -t $@

run_perforce:
	cd perforce; docker run -d -e SERVER_NAME=perforce -e P4PASSWD=abcd123efg -p 1667:1666 --name=perforce perforce
