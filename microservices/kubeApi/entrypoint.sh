#!/bin/sh

uvicorn main:app --host 0.0.0.0 --port 8080 --log-level "${LOG_LEVEL:-"debug"}" --reload