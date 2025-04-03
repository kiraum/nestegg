#!/bin/bash

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Compile TypeScript to JavaScript
echo "Compiling TypeScript..."
npx tsc

echo "Build complete!"
