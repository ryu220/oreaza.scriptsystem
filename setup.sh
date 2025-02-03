#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install streamlit
pip install langchain-anthropic
pip install langchain
chmod +x app.py
rm setup.sh
