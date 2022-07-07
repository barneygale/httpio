#
# Makefile include file to include standard docker targets
# Do not include directly, is used by docker.mk and run_locally.mk

ifeq "${VERSION_IN_PYTHON}" ""
VERSION_IN_PYTHON:=${VERSION}
endif

BUILD_TAG?=local
DOCKER_REPO?=bbcrd
DOCKER?=docker

MS_DOCKERFILE?=Dockerfile.multi
MS_DOCKERFILE_TEMPLATE?=Dockerfile_multi.j2

ifneq "${FORGE_CERT}" ""
	EXTRA_DOCKER_BUILD_ARGS += --secret id=forgecert,src=${FORGE_CERT}
endif

MS_DOCKER_BUILD_ARGS:=\
	-f ${MS_DOCKERFILE} \
	--build-arg VERSION=${VERSION_IN_PYTHON} \
	--build-arg BUILD_TAG=${BUILD_TAG} \
	--build-arg CLOUDFIT_BASE_NAME=${CLOUDFIT_BASE_NAME} \
	--build-arg CLOUDFIT_BASE_LABEL=${CLOUDFIT_BASE_LABEL} \
	${EXTRA_DOCKER_BUILD_ARGS}
MS_DOCKER_BUILD?=DOCKER_BUILDKIT=1 ${DOCKER} build ${MS_DOCKER_BUILD_ARGS}

EXTRA_DOCKER_RUN_ARGS?=

BUILD_ARTEFACT?=

# If this is an interactive shell (or at least, STDIN is a terminal), attach a terminal when running containers
INTERACTIVE:=$(shell [ -t 0 ] && echo 1)
ifeq ($(INTERACTIVE), 1)
	EXTRA_DOCKER_RUN_ARGS += -ti
endif

# Set this to prompt another directory (e.g. a common layer) to build first
BASE_MOD_DIR?=

check-allow-local-wheels:
ifneq ($(ALLOW_LOCAL_WHEELS),TRUE)
ifneq ($(shell ls -A "$(topbuilddir)/wheels" 2> /dev/null),)
	$(error Wheels directory $(topbuilddir)/wheels is not empty. Set environment variable ALLOW_LOCAL_WHEELS to TRUE to allow wheels)
endif
endif

ifneq "${BASE_MOD_DIR}" ""
ms_docker-build-base:
	$(MAKE) -C ${BASE_MOD_DIR} ms_docker-build
else
ms_docker-build-base: ;
endif

# These generic targets can be used to trigger various types of docker builds, they aren't intended
# to be directly used by users, but instead are an api for other makefile targets to make use of
ms_docker-build: check-allow-local-wheels ${BUILD_ARTEFACT} ${MS_DOCKERFILE} $(topbuilddir)/wheels prepcode ms_docker-build-base
	${MS_DOCKER_BUILD} --target layer -t ${MODNAME}:${BUILD_TAG} .

# This target builds the "layer" stage and add the image name suffix to _alt_<alt name>. This target can be
# use on conjunction with the CLOUDFIT_BASE_NAME option to build the "layer" using a different base image.
ms_docker-alt-build-%: check-allow-local-wheels ${BUILD_ARTEFACT} ${MS_DOCKERFILE} $(topbuilddir)/wheels prepcode ms_docker-build-base
	${MS_DOCKER_BUILD} --target layer -t ${MODNAME}_alt_$*:${BUILD_TAG} .

MOD_WITH_API?=false
ifeq "$(MOD_WITH_API)" "true"
ms_docker-build: ms_external-layer-docker-build-api
endif

# NOTE: Addition of prerequisits to pattern rules doesn't work as expected, hence alternet definition of
# full target definition
ifeq "$(MOD_WITH_API)" "true"
ms_docker-build-%: check-allow-local-wheels ${BUILD_ARTEFACT} ${MS_DOCKERFILE} $(topbuilddir)/wheels prepcode ms_docker-build-base ms_external-layer-docker-build-api
else
ms_docker-build-%: check-allow-local-wheels ${BUILD_ARTEFACT} ${MS_DOCKERFILE} $(topbuilddir)/wheels prepcode ms_docker-build-base
endif
	${MS_DOCKER_BUILD} --target $* -t ${MODNAME}_$*:${BUILD_TAG} .

ms_external-layer-docker-build-%:
	${MAKE} -C ${project_root_dir}/$* ms_docker-build

ms_docker-run: ms_docker-build
	docker run --rm ${EXTRA_DOCKER_RUN_ARGS} ${MODNAME}:${BUILD_TAG}

ms_docker-run-%: ms_docker-build-%
	docker run --rm ${EXTRA_DOCKER_RUN_ARGS} ${MODNAME}_$*:${BUILD_TAG}

ms_docker-push: ms_docker-ver-push-$(DOCKERISED_VERSION)

ms_docker-ver-push-%: push-check-changes ms_docker-build
	docker tag $(MODNAME):$(BUILD_TAG) $(DOCKER_REPO)/$(MODNAME):$*
	docker push $(DOCKER_REPO)/$(MODNAME):$*

ms_docker-push-%: push-check-changes ms_docker-build-%
	docker tag $(MODNAME)_$*:$(BUILD_TAG) $(DOCKER_REPO)/$(MODNAME)_$*:$(DOCKERISED_VERSION)
	docker push $(DOCKER_REPO)/$(MODNAME)_$*:$(DOCKERISED_VERSION)

ms_docker-push-latest-%: push-check-changes ms_docker-build-%
	docker tag $(MODNAME)_$*:$(BUILD_TAG) $(DOCKER_REPO)/$(MODNAME)_$*:latest
	docker push $(DOCKER_REPO)/$(MODNAME)_$*:latest

ms_docker-clean:
	-for IMG in $$(docker images | grep '${MODNAME}' | grep '${BUILD_TAG}' | awk '{print $$1":"$$2}'); do docker rmi $$IMG; done

CLEAN_FILES+=externals.json
EXTRA_GITIGNORE_LINES+=externals.json

# externals.json passes parameter values into the Dockerfile template
$(topbuilddir)/externals.json:
	@echo '{' > $@
	@echo '    "with_api": ${MOD_WITH_API},' >> $@
	@echo '    "modname": "${MODNAME}"' >> $@
	@echo '}' >> $@

# The dockerfile itself
${MS_DOCKERFILE}: $(MS_DOCKERFILE_TEMPLATE) $(commontooling_dir)/docker/Dockerfile_multi_macros.j2 $(topbuilddir)/externals.json
	$(J2) $< externals.json > $@

.PHONY: check-allow-local-wheels ms_docker-build ms_docker-run ms_docker-clean ms_docker-push ms_docker-build-source