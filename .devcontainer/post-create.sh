#!/bin/bash
set -e

sudo apt update
pip install --upgrade pip 
pip install -r agentic_ai/applications/requirements.txt