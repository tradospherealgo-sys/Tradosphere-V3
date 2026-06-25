#!/bin/bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
exec gunicorn wsgi:app
