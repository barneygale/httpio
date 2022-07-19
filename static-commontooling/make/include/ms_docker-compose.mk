#
# Makefile include file to include standard docker-compose targets
# Do not include directly, is used by docker.mk and run_locally.mk

BUILD_TAG?=local

COMPOSE_PROJECT_NAME?=$(BUILD_TAG)_$(MODNAME)
DOCKER_COMPOSE_EXTRA_ENV?=

ifneq "${FORGE_CERT}" ""
	DOCKER_COMPOSE_EXTRA_ENV += FORGE_CERT=$(FORGE_CERT)
endif

DOCKER_COMPOSE_ENV=\
	MODNAME=$(MODNAME) \
	BUILD_TAG=$(BUILD_TAG) \
	$(DOCKER_COMPOSE_EXTRA_ENV)
DOCKER_COMPOSE?=$(DOCKER_COMPOSE_ENV) docker-compose -p $(COMPOSE_PROJECT_NAME)

ms_docker-compose-run-%:
	$(DOCKER_COMPOSE) run --rm $*

ms_docker-compose-stop-%:
	$(DOCKER_COMPOSE) stop $*

ms_docker-compose-rm-%:
	$(DOCKER_COMPOSE) rm -f $*

ms_docker-compose-images:
	$(DOCKER_COMPOSE) images

ms_docker-compose-ps:
	$(DOCKER_COMPOSE) ps

.PHONY: ms_docker-compose-images ms_docker-compose-ps