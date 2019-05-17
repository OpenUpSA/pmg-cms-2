#!/bin/sh -ex
#
# Update requirements files from Pipfile.lock

pipenv lock --requirements >requirements.txt
pipenv lock --requirements --dev >requirements-dev.txt
