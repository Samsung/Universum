UNIVERSUM_ENVIRONMENT=$(filter-out Makefile perforce, $(wildcard *))
DOCKER_ARGS :=
PYTHON ?= $(shell python -c 'import sys; print("python%d.%d"% sys.version_info[0:2])' )
ifeq ($(PYTHON),)
PYTHON := python3.7
endif

.PHONY: all $(UNIVERSUM_ENVIRONMENT) run_perforce perforce

all: $(UNIVERSUM_ENVIRONMENT) perforce

$(UNIVERSUM_ENVIRONMENT):
	docker build --build-arg PYTHON=$(PYTHON) $(DOCKER_ARGS) $@ -t $@_$(PYTHON)

perforce:
	docker build $(DOCKER_ARGS) $@ -t $@

run_perforce:
	cd perforce; docker run -d -e SERVER_NAME=perforce -e P4PASSWD=abcd123efg -p 1667:1666 --name=perforce perforce
