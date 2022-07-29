# Tooling for calling and using docker in our makefiles
#
# Configurable variables:
#
#    MODNAME?=
#       The name of the module being built (no default, must be set, if you have already included pythonic.mk then that will set it)
#
#    VERSION?=
#       The version of the module being built (no default, must be set, if you have already included pythonic.mk then that will set it)
#
#    topdir?=
#       The top directory. If you've included our other Makefile tooling this will already be set.
#
#    topbuilddir?=
#       The top build directory. If you've included our other Makefile tooling this will already be set.
#
#    project_root_dir?=
#       The project root directory. If you've included our other Makefile tooling this will already be set.
#
#    BUILD_ARTEFACT?=$(topbuilddir)/requirements.txt $(topbuilddir)/constraints.txt
#       The build artefacts which are needed to construct the layer docker image. This default will work well with pythonic.mk
#
#    ALLOW_LOCAL_WHEELS?=FALSE
#       Set to TRUE to allow wheel files in the wheels/ directory which are then used in the docker build
#
#    FORGE_CERT?=$(realpath $(HOME)/.certs/devcert.pem)
#       The location of the file for the forgecert secret
#
#    BUILD_TAG?=local
#       A unique tag identifying the current build
#
#    BASE_MOD_DIR?=
#       Directory containing the Docker image this one is based on. If set, that directory's ms_docker-build will be a prerequisite
#
#    DOCKER_REPO?=
#       A docker repo to push images to
#
#    MS_DOCKERFILE?=Dockerfile.multi
#       The path to the Dockerfile to use
#
#    EXTRA_DOCKER_BUILD_ARGS?=
#       Any extra args to add to runs of docker build
#
#    EXTRA_DOCKER_RUN_ARGS?=
#       Any extra args to add to runs of docker run
#
#    MOD_WITH_API?=false
#       If set to true, will generate and pull an external API layer into the source layer
#       Remember to list any files you wish to be included in the package using in MANIFEST.in using <MODNAME>/apidocs
#       as the base. Otherwise they WILL NOT be available to your code/tests/etc.
#
#    MS_DOCKER_ARTEFACT?=TRUE
#       Set to FALSE to not automatically run ms_docker-build when make artefact is run
#
#    MS_DOCKER_SOURCE?=TRUE
#       If set to true, will build a source stage before building a layer stage
#
#    MS_DOCKER_CLEAN?=TRUE
#       Set to FALSE to not automatically clean up docker images when make clean is run
#
#    MS_DOCKER_UNITTEST?=TRUE
#       Set to FALSE to not automatically run ms_docker-run-unittest when make test is run
#
#    MS_DOCKER_FLAKE8?=TRUE
#       Set to FALSE to not automatically run ms_docker-run-flake8 when make lint is run
#
#    MS_DOCKER_MYPY?=TRUE
#       Set to FALSE to not automatically run ms_docker-run-mypy when make mypy is run
#
#    MS_DOCKER_WHEEL?=TRUE
#       Set to FALSE to not automatically run ms_docker-run-wheel when make wheel is run
#
#    MS_DOCKER_DOCS?=TRUE
#       Set to FALSE to not automatically run ms_docker-run-docs when make docs is run
#
#    MS_DOCKER_PUSH?=FALSE
#       Set to TRUE to automatically run ms_docker-push when make push is run
#
#    MS_DOCKER_PUSH_LATEST?=FALSE
#       Set to TRUE to automatically run ms_docker-push-latest when make push is run, i.e. push with the "latest" tag
#
#    CLOUDFIT_BASE_NAME?=python
#
#    CLOUDFIT_BASE_LABEL?=latest
#       Set to something other than latest to use a different cloudfit base image build (e.g. python3.9)
#
#
#   Targets you may find useful to reference in your Makefiles:
#
#   ms_docker-build
#      builds the "layer" stage from the Dockerfile and names it as ${MODNAME}:${BUILD_TAG}
#
#   ms_docker-build-<stage name>
#      builds the "<stage name>" layer from the Dockerfile and names it as ${MODNAME}_<stage name>:${BUILD_TAG}
#
#   ms_docker-run
#      Builds the "layer" stage from the Dockerfile and runs the image ${MODNAME}:${BUILD_TAG}
#
#   ms_docker-run-<stage name>
#      builds the "<stage name>" layer from the Dockerfile and runs the image ${MODNAME}_<stage name>:${BUILD_TAG}
#
#   ms_external-layer-<layer name>-docker-build
#      runs the ms_docker-build target on the directory ${project_root_dir}/<layer name>
#
#   ms_docker-push
#      Builds the "layer" stage from the Dockerfile and pushes it as ${DOCKER_REPO}/${MODNAME}:${DOCKERISED_VERSION}
#
#   ms_docker-push-<stage name>
#      builds the "<stage name>" layer from the Dockerfile and pushes it as ${DOCKER_REPO}/${MODNAME}_<stage name>:${DOCKERISED_VERSION}
#
#   ms_docker-clean
#      removes all docker images with a name containing ${MODNAME} and tag ${BUILD_TAG} on the local system
#
#
#   In addition after importing this file the following variables have been populated
#
#      MS_DOCKER_BUILD
#         Contains the executable command to run docker build with the correct settings and build-args set Extra arguments can be added after it
#
#      DOCKER_COMPOSE
#         Contains the executable command to run docker-compose with the correct settings and build-args set. Extra arguments can be added after it
#


BUILD_ARTEFACT?=$(topbuilddir)/requirements.txt $(topbuilddir)/constraints.txt
EXTRA_DOCKER_RUN_ARGS?=
BASE_MOD_DIR?=
ALLOW_LOCAL_WHEELS?=FALSE

ifndef DOCKER_TAGS
export DOCKER_TAGS := $(shell $(PBRVERSION) --docker-tag)
ifeq (,$(DOCKER_TAGS))
  $(error "pbrversion failure: $(DOCKER_TAGS)")
endif
endif

PUSH_TAGS=$(patsubst %,ms_docker-ver-push-%,$(DOCKER_TAGS))


all: docker-help
include $(commontooling_dir)/make/include/ms_docker.mk
include $(commontooling_dir)/make/include/ms_docker-compose.mk
include $(commontooling_dir)/make/include/dockerignore.mk
-include $(commontooling_dir)/make/artifactory_caretaker.mk


# Some standard patterns with some variables to turn them on and off
MS_DOCKER_ARTEFACT?=TRUE
ifeq "${MS_DOCKER_ARTEFACT}" "TRUE"
artefact: ms_docker-build
endif

MS_DOCKER_SOURCE?=TRUE
ifeq "${MS_DOCKER_SOURCE}" "TRUE"
ifneq "${CLOUDFIT_MAKE_MODE}" "api"
ms_docker-build: ms_docker-build-source
endif
endif

MS_DOCKER_CLEAN?=TRUE
ifeq "${MS_DOCKER_CLEAN}" "TRUE"
clean: ms_docker-clean
CLEAN_FILES+=$(MS_DOCKERFILE)
EXTRA_GITIGNORE_LINES+=$(MS_DOCKERFILE)
endif

MS_DOCKER_UNITTEST?=TRUE
ifeq "${MS_DOCKER_UNITTEST}" "TRUE"
test: ms_docker-run-unittest
endif

MS_DOCKER_FLAKE8?=TRUE
ifeq "${MS_DOCKER_FLAKE8}" "TRUE"
ms_docker-build-flake8: $(topdir)/.flake8
lint: ms_docker-run-flake8
endif

MS_DOCKER_MYPY?=TRUE
ifeq "${MS_DOCKER_MYPY}" "TRUE"
ifeq "${COMMONTOOLING_BUILD_ENV}" "internal"
ms_docker-build-mypy: $(topdir)/.mypy.ini
endif
ifneq "${FORGE_CERT}" ""
ms_docker-run-mypy: EXTRA_DOCKER_RUN_ARGS+=--mount type=bind,source=${FORGE_CERT},target=/run/secrets/forgecert,readonly
endif
mypy: ms_docker-run-mypy
endif

$(topbuilddir)/.tmp/run_with_dir_modes.sh: $(commontooling_dir)/misc/run_with_dir_modes.sh $(topbuilddir)/.tmp
	cp $< $@

MS_DOCKER_WHEEL?=TRUE
ifeq "${MS_DOCKER_WHEEL}" "TRUE"

ms_docker-build-wheel: $(topbuilddir)/.tmp/run_with_dir_modes.sh $(topbuilddir)/.tmp/_full_version.py

ms_docker-run-wheel: EXTRA_DOCKER_RUN_ARGS+=--mount type=bind,source=${topbuilddir}/dist,target=/${MODNAME}/dist
$(WHEEL_FILE): ms_docker-run-wheel

# NOTE: The wheel docker stage also generates sdist distributable tarballs
$(SDIST_FILE): ms_docker-run-wheel
endif

MS_DOCKER_DOCS?=TRUE
ifeq "${MS_DOCKER_DOCS}" "TRUE"
$(topdir)/docs:
	mkdir -p $@

ms_docker-build-docs: $(topbuilddir)/.tmp/run_with_dir_modes.sh $(topbuilddir)/.tmp/_full_version.py

ms_docker-run-docs: EXTRA_DOCKER_RUN_ARGS+=--mount type=bind,source=${topbuilddir}/docs,target=/docs
docs: $(topbuilddir)/docs ms_docker-run-docs
$(topbuilddir)/docs/$(MODNAME)/index.html: $(topbuilddir)/docs ms_docker-run-docs
endif

upload-docker:

enable_push=FALSE
ifneq "${VERSION}" "${NEXT_VERSION}"
enable_push=TRUE
else ifneq "${BUILD_TAG}" "local"
enable_push=TRUE
endif

HELP_PUSH_TAGS:=
ifeq "${enable_push}" "TRUE"
MS_DOCKER_PUSH?=FALSE
ifeq "${MS_DOCKER_PUSH}" "TRUE"
HELP_PUSH_TAGS+=${DOCKER_TAGS}
push: $(PUSH_TAGS)
upload-docker: $(PUSH_TAGS)
endif

MS_DOCKER_PUSH_LATEST?=FALSE
ifeq "${MS_DOCKER_PUSH_LATEST}" "TRUE"
HELP_PUSH_TAGS+=latest
push: ms_docker-ver-push-latest
upload-docker: ms_docker-ver-push-latest
endif
else
no-push-warn:
	$(warning Docker images won't be pushed for tag build outside of CI)
push: no-push-warn
upload-docker: no-push-warn
endif

$(topbuilddir)/wheels:
	mkdir -p $@

docker-help:
ifeq "${MS_DOCKER_ARTEFACT}" "TRUE"
	@echo "make artefact          - Build the docker container for this layer"
endif
ifeq "${MS_DOCKER_UNITTEST}" "TRUE"
	@echo "make test              - Run unit tests in docker"
endif
ifeq "${MS_DOCKER_FLAKE8}" "TRUE"
	@echo "make lint              - Run flake8 on python code"
endif
ifeq "${MS_DOCKER_MYPY}" "TRUE"
	@echo "make mypy              - Run mypy on python code"
endif
ifeq "${MS_DOCKER_WHEEL}" "TRUE"
	@echo "make wheel             - Make wheel for layer"
endif
ifneq "${HELP_PUSH_TAGS}" ""
	@echo "make push              - Push docker image to $(DOCKER_REPO) with tags: $(HELP_PUSH_TAGS)"
endif
ifeq "${MS_DOCKER_DOCS}" "TRUE"
	@echo "make docs              - Make documentation for layer"
endif
	@if [ -f docker-compose.yml ]; then \
		echo ""; \
		echo "You can also run docker-compose using the command:"; \
		echo "  $(DOCKER_COMPOSE) <ARGS>"; \
	fi

.PHONY: docker-help upload-docker ms_docker-compose-images ms_docker-compose-ps push-check-changes
