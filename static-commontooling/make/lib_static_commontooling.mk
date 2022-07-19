#
# Makefile include file to update static commontooling files when needed
#

# Set up basic directories, assuming a Makefile in the top of a service
ifndef topdir
NUM_OF_PARENT:=$(shell echo $$(( $(words $(MAKEFILE_LIST)) - 1)) )
topdir?=$(realpath $(dir $(word $(NUM_OF_PARENT),$(MAKEFILE_LIST))))
project_root_dir?=$(topdir)
commontooling_dir?=$(project_root_dir)/static-commontooling
endif

COMMONTOOLING_BUILD_ENV:=os
static_commontooling_list:=os_lib_file_list

-include $(project_root_dir)/commontooling/make/include/update_static_commontooling.mk
