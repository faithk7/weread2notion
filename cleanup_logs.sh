#!/bin/bash
# This script removes all files ending with .log from the project root directory.

find . -maxdepth 1 -name "*.log" -print -delete

echo "Log files cleaned up."