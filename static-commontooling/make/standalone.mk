#
# Makefile include file to include standard cloudfit tooling for a standalone project
# Should usually be the first file included in Makefile

#
# Before inclusing you may want to set the following variables:
#
#    EXTRA_GITIGNORE_LINES?=
#       Add extra lines that should appear in the generated .gitignore file
#
#
#    PYTHON_VERSION?=
#       Override the default Python version, and use that version of tools containers as well
#
#   OASSPECROOTDIR?=$(project_root_dir)/api/
#       The directory in which all the specs located
#
#
# In addition, some variables can be overidden to change the versions of tools used by this Makefile. These can either
# be set in your Makefile, or as environment variables before running Make, although it's unlikely you'll want to
# override them permanently on a per-repo basis
#
#    J2CLI_DOCKER_CONTAINER?=bbcrd/j2cli
#       Change the container image used for processing Jinja templates, such as to one built locally
#
#    J2CLI_DOCKER_LABEL?=latest
#       Change the label used for the Jinja template container. Note that the default is `latest` unless PYTHON_VERSION
#       is set, in which case it defaults to the one corresponding to that Python version.
#
#    PBRVERSION_CONTAINER?=bbcrd/pbrversion
#       Change the container image used for calculating version numbers, such as to one built locally
#
#    PBRVERSION_VERSION?=
#       Change the label used for the pbrversion container
#

CLOUDFIT_MAKE_MODE=standalone

EXTRA_GITIGNORE_LINES?=
MOD_WITH_API?=false

# Set up basic directories, assuming a Makefile in a layer directory
ifndef topdir
NUM_OF_PARENT:=$(shell echo $$(( $(words $(MAKEFILE_LIST)) - 1)) )
topdir:=$(realpath $(dir $(word $(NUM_OF_PARENT),$(MAKEFILE_LIST))))
project_root_dir?=$(topdir)
commontooling_dir?=$(project_root_dir)/commontooling
endif

include $(commontooling_dir)/make/include/core.mk
-include $(project_root_dir)/commontooling/make/include/jenkinsfile.mk
-include $(project_root_dir)/commontooling/make/include/pull_request_template.mk
include $(commontooling_dir)/make/include/gitignore.mk

.PHONY: prepcode
