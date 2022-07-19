#!/bin/bash

#
# Clone the commontooling repository
# NOTE: Commontooling is an internal library. This script will not function external to BBCRD.
# Open-source repos contain a static copy of relevant parts of Commontooling and only use this
# script to keep that copy up to date.
#

set -e

BRANCH=$1

if [ -z "$BRANCH" ]
then
    BRANCH="main"
fi

if [ ! -d "commontooling" ]
then
    git clone git@github.com:bbc/rd-cloudfit-commontooling.git commontooling --depth=1 --no-single-branch --branch=$BRANCH
fi

cd commontooling
git checkout $BRANCH
git pull
