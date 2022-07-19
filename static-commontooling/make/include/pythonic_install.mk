#
# Makefile include file to configure install targets for standard and editable installs of Python code, either for
# individual layers or an entire service
#

# If running from service.mk, the Python interpreter needs to be located
ifeq "$(PYTHON3)" ""
PYTHON3=$(eval PYTHON3 := $(shell which python3))$(value PYTHON3)
endif

all: help-install

check-in-virtualenv:
ifneq ($(ALLOW_INSTALL_OUTSIDE_VIRTUALENV),TRUE)
ifeq ($(VIRTUAL_ENV),)
	$(error make install should generally be used in a virtualenv. Either activate a virtualenv, or set ALLOW_INSTALL_OUTSIDE_VIRTUALENV=TRUE)
endif
endif

ifeq "$(CLOUDFIT_MAKE_MODE)" "service"
# If this is a service (this file was included from service.mk), we need to install all the layers that make up the
# service in a single command so that their co-dependencies get satisfied together

SKIP_PYTHON_INSTALL?=
PYTHON_INSTALL_PKGS=$(filter-out $(SKIP_PYTHON_INSTALL), $(CHILD_PKGS))

# Layers to install before any others in service
PYTHON_INSTALL_FIRST?=common fixtures

# Remaining layers to install
PYTHON_INSTALL_SECOND:=$(filter-out $(PYTHON_INSTALL_FIRST), $(PYTHON_INSTALL_PKGS))

# Re-calculate _FIRST in case items in it don't actually exist in CHILD_PKGS (i.e. one of the default layers doesn't exists)
PYTHON_INSTALL_FIRST:= $(filter-out $(PYTHON_INSTALL_SECOND), $(PYTHON_INSTALL_PKGS))

# Install target patterns. NOTE: The actual pattern targets are defined in service.mk
CHILD_DIRS_INSTALL_FIRST:=$(addsuffix -install,$(PYTHON_INSTALL_FIRST))
CHILD_DIRS_INSTALL_SECOND:=$(addsuffix -install,$(PYTHON_INSTALL_SECOND))
CHILD_DIRS_EDITABLE_INSTALL_FIRST:=$(addsuffix -editable-install,$(PYTHON_INSTALL_FIRST))
CHILD_DIRS_EDITABLE_INSTALL_SECOND:=$(addsuffix -editable-install,$(PYTHON_INSTALL_SECOND))

EXTRA_INSTALL_REQUIREMENTS?=

INSTALL_TEST_REQUIREMENTS?=TRUE
ifeq "$(INSTALL_TEST_REQUIREMENTS)" "TRUE"
EXTRA_INSTALL_REQUIREMENTS += $(patsubst %,-r src/%/test-requirements.txt,$(PYTHON_INSTALL_PKGS))
endif

install: check-in-virtualenv
	$(MAKE) install-first
	$(MAKE) install-second

install-first: $(CHILD_DIRS_INSTALL_FIRST)
install-second: $(CHILD_DIRS_INSTALL_SECOND)

editable-install: check-in-virtualenv
	$(MAKE) editable-install-first
	$(MAKE) editable-install-second

editable-install-first: $(CHILD_DIRS_EDITABLE_INSTALL_FIRST)
editable-install-second: $(CHILD_DIRS_EDITABLE_INSTALL_SECOND)


else  # from ifeq "$(CLOUDFIT_MAKE_MODE)" "service"
# This is a layer or tool, so it can be installed on its own

install: install-pythonic

EXTRA_INSTALL_REQUIREMENTS?=-r $(topbuilddir)/test-requirements.txt

install-pythonic: check-in-virtualenv
	$(PYTHON3) -m pip install $(EXTRA_INSTALL_ARGS) $(topbuilddir) $(EXTRA_INSTALL_REQUIREMENTS)

editable-install: check-in-virtualenv
	$(PYTHON3) -m pip install $(EXTRA_INSTALL_ARGS) -e $(topbuilddir) $(EXTRA_INSTALL_REQUIREMENTS)

endif  # from ifeq "$(CLOUDFIT_MAKE_MODE)" "service"

help-install:
	@echo "make install                     - Install on local system (only for use during development)"
	@echo "make editable-install            - Make an editable install on local system (only for use during development)"

.PHONY: check-in-virtualenv