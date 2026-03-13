#!/bin/sh

exec uvicorn csit_validation.main:app --host 0.0.0.0 --port 8080 