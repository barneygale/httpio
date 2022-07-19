#
# Makefile include file to include standard cloudfit tooling for python packages
# Should usually be the second file included in Makefile
#
# Most of the actual recipes for building/running Python code are handled by docker.mk, which should usually be included
# after this file (a previous version also allowed using tox, but that has since been deprecated and removed)

#
# Before including you may want to set the following variables:
#
#    USE_VERSION_FILE?=TRUE
#		By default builds get a generated _version.py file. Set this to FALSE to disable this
#
#    TWINE_REPO?=
#    	Change the default wheel upload location (if blank, open source repositories get PyPI, internal repositories get Artifactory)
#
#    TWINE_REPO_USERNAME?= & TWINE_REPO_PASSWORD?=
#    	Set these in the environment when uploading wheels (or CI sets them automatically)
#
#    EXTRA_INSTALL_REQUIREMENTS?=-r test-requirements.txt
#       Add extra packages to install when running make install/make editable-install
#
#    MOD_WITH_API?=false
#       If set to true, will generate and pull an external API layer into the source layer
#       Remember to list any files you wish to be included in the package using in MANIFEST.in using <MODNAME>/apidocs as the base.
#       Otherwise they WILL NOT be available to your code/tests/etc.
#

USE_VERSION_FILE?=TRUE
MOD_WITH_API?=false

# Extract version and module name from working tree
ifeq "$(PROJECT)" ""
PROJECT=$(eval PROJECT := $(shell $(DOCKER) run --rm -v $(topdir):/data:ro python:3.10 python /data/setup.py --name))$(value PROJECT)
endif
ifeq "$(GITCOMMIT)" ""
GITCOMMIT=$(eval GITCOMMIT := $(shell git rev-parse --short HEAD))$(value GITCOMMIT)
endif

MODNAME?=$(PROJECT)

ifeq "$(MOD_WITH_API)" "true"
-include $(commontooling_dir)/make/specs.mk
endif

CLEAN_FILES += $(topbuilddir)/dist

# Identify the source files for pythonic code
PYTHONIC_SOURCES:=$(eval PYTHONIC_SOURCES := $(shell find $(topdir)/$(MODNAME) -type f -name '*.py') $(topdir)/setup.py $(topdir)/MANIFEST.in $(topdir)/setup.cfg)$(value PYTHONIC_SOURCES)
PYTHONIC_TEST_SOURCES:=$(eval PYTHONIC_TEST_SOURCES := $(shell find $(topdir)/tests -type f -name '*.py') $(topdir)/test-requirements.txt)$(value PYTHONIC_TEST_SOURCES)

# Add extra dependencies to the core targets
all: help-pythonic

ifeq "${BUILD_TAG}" "local"
VERSION_IN_PYTHON=${NEXT_VERSION}
else
VERSION_IN_PYTHON=${VERSION}
endif

WHEEL_FILE?=$(topbuilddir)/dist/$(MODNAME)-$(VERSION)-py3-none-any.whl
SDIST_FILE?=$(topbuilddir)/dist/$(MODNAME)-$(VERSION).tar.gz

wheel: $(WHEEL_FILE)
source: source-pythonic
source-pythonic: $(SDIST_FILE)

$(WHEEL_FILE): $(topbuilddir)/dist
$(SDIST_FILE): $(topbuilddir)/dist

$(topbuilddir)/dist:
	mkdir -p $@

prepcode: $(EXTRA_MODS_REQUIRED_VERSIONFILE)

# Extract dependency requirements and constraints from setup.py
PY_REQ_EX_CONTAINER?=bbcrd/pyreqex
PY_REQ_EX_VERSION?=latest
PY_REQ_EX_CMD:=$(DOCKER) run --rm -v $(topdir):/data:ro $(PY_REQ_EX_CONTAINER):$(PY_REQ_EX_VERSION)
$(topbuilddir)/requirements.txt: $(topdir)/setup.py
	$(PY_REQ_EX_CMD) $(<F) > $@

$(topbuilddir)/constraints.txt: $(topdir)/setup.py
	$(PY_REQ_EX_CMD) $(<F) --constraints > $@

CLEAN_FILES += $(topbuilddir)/requirements.txt
CLEAN_FILES += $(topbuilddir)/constraints.txt

MISC_FILES+=$(topdir)/.flake8

ifeq "${COMMONTOOLING_BUILD_ENV}" "internal"
MISC_FILES+=$(topdir)/setup.cfg
EXTRA_GITIGNORE_LINES+=setup.cfg
endif

include $(commontooling_dir)/make/include/miscfiles.mk
include $(commontooling_dir)/make/include/pythonic_install.mk

#VERSION file tooling for layers, not used by standalone libraries
ifeq "$(USE_VERSION_FILE)" "TRUE"
include $(commontooling_dir)/make/include/pythonic_version.mk
endif

TWINE_REPO?=
TWINE_REPO_USERNAME?=
TWINE_REPO_PASSWORD?=

TWINE_VOLUMES=-v $(shell realpath $(topdir)):/data:ro

TWINE_FLAGS= \
	--skip-existing \
	--non-interactive

ifneq "${TWINE_REPO}" ""
	TWINE_FLAGS += --repository-url ${TWINE_REPO}
endif

ifneq "${TWINE_REPO_USERNAME}" ""
	TWINE_FLAGS += -u ${TWINE_REPO_USERNAME}
endif

ifneq "${TWINE_REPO_PASSWORD}" ""
	TWINE_FLAGS += -p ${TWINE_REPO_PASSWORD}
endif

TWINE_FLAGS += ${EXTRA_TWINE_FLAGS}

ifeq "${COMMONTOOLING_BUILD_ENV}" "internal"
ifneq "${FORGE_CERT}" ""
TWINE_VOLUMES += -v $(FORGE_CERT):/devcert.pem:ro
TWINE_FLAGS += --client-cert /devcert.pem
endif
endif

TWINE=$(DOCKER) run --rm $(TWINE_VOLUMES) bbcrd/twine

enable_push=TRUE
ifneq "${COMMONTOOLING_BUILD_ENV}" "internal"
ifneq "${NEXT_VERSION}" "${VERSION}"
enable_push=FALSE
endif
endif

ifeq "${enable_push}" "TRUE"
WHEEL_FILE_IN_CONTAINER=/data/$(shell realpath --relative-to $(topdir) $(WHEEL_FILE))
SDIST_FILE_IN_CONTAINER=/data/$(shell realpath --relative-to $(topdir) $(SDIST_FILE))

upload-wheels: upload-wheel
upload-wheel: push-check-changes $(WHEEL_FILE) $(SDIST_FILE)
	$(TWINE) upload $(TWINE_FLAGS) $(WHEEL_FILE_IN_CONTAINER) $(SDIST_FILE_IN_CONTAINER)
else
no-push-warn:
	$(warning Dev wheels can't be pushed on external build environments)
upload-wheels: no-push-warn
upload-wheel: no-push-warn
endif

help-pythonic:
	@echo "make source                      - Create source package"
	@echo "make upload-wheel                - Upload wheels to ${TWINE_REPO}"

.PHONY: source-pythonic install-pythonic help-pythonic clean-pythonic prepcode install source wheel upload-wheel
