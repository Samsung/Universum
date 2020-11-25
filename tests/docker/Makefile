DOCKER_TARGETS=$(filter-out Makefile, $(wildcard *))
DOCKER_ARGS :=
PYTHON := none

.PHONY: all $(DOCKER_TARGETS) run_perforce

all: $(DOCKER_TARGETS)

$(DOCKER_TARGETS):
	if [ $@ = 'perforce' ]; then \
  	docker build $(DOCKER_ARGS) $@ -t $@; \
	else \
	docker build --build-arg PYTHON=$(PYTHON) $(DOCKER_ARGS) $@ -t $@_$(PYTHON); \
	fi

run_perforce:
	cd perforce; docker run -d -e SERVER_NAME=perforce -e P4PASSWD=abcd123efg -p 1667:1666 --name=perforce perforce
