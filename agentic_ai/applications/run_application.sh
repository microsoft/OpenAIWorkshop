#!/bin/bash		
export PYTHONPATH="$(cd "$(dirname "$0")/.."; pwd)"		
python backend.py &		
streamlit run frontend.py	