DOCKER_TARGETS=$(filter-out Makefile, $(wildcard *))

.PHONY: all $(DOCKER_TARGETS) run_perforce

all: $(DOCKER_TARGETS)

$(DOCKER_TARGETS):
	docker build $@ -t $@

run_perforce:
	+$(MAKE) -C perforce test_run
