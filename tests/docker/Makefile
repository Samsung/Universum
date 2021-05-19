UNIVERSUM_ENVIRONMENT= universum_test_env universum_test_env_no_p4 universum_test_env_no_vcs
DOCKER_ARGS :=
PYTHON ?= $(shell python -c 'import sys; print("python%d.%d"% sys.version_info[0:2])' )
ifeq ($(PYTHON),)
PYTHON := python3.7
endif

.PHONY: all $(UNIVERSUM_ENVIRONMENT) run_perforce perforce

all: $(UNIVERSUM_ENVIRONMENT) perforce

$(UNIVERSUM_ENVIRONMENT):
	docker build --target $@ --build-arg PYTHON=$(PYTHON) $(DOCKER_ARGS) universum_test_env -t $@_$(PYTHON)

perforce:
	docker build $(DOCKER_ARGS) $@ -t $@

run_perforce:
	cd perforce; docker run -d -e SERVER_NAME=perforce -e P4PASSWD=abcd123efg -p 1667:1666 --name=perforce perforce
