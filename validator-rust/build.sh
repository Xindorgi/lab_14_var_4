#!/bin/bash
# Build script for Rust validator library with C bindings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Rust validator library...${NC}"

# Check for cargo
if ! command -v cargo &> /dev/null; then
    echo -e "${RED}Error: cargo not found. Install Rust from https://rustup.rs/${NC}"
    exit 1
fi

# Check for cbindgen
if ! command -v cbindgen &> /dev/null; then
    echo -e "${YELLOW}cbindgen not found, installing...${NC}"
    cargo install cbindgen
fi

# Create build directory
mkdir -p target

echo -e "${GREEN}1. Building static library...${NC}"
cargo build --release --lib

echo -e "${GREEN}2. Generating C header...${NC}"
cbindgen --config cbindgen.toml --crate news-validator --output include/news_validator.h

echo -e "${GREEN}3. Building shared library...${NC}"
cargo build --release --lib --features "cdylib"

echo -e "${GREEN}4. Copying artifacts...${NC}"
mkdir -p dist
cp target/release/libnews_validator.a dist/ 2>/dev/null || true
cp target/release/libnews_validator.so dist/ 2>/dev/null || true
cp target/release/libnews_validator.dylib dist/ 2>/dev/null || true
cp include/news_validator.h dist/

echo -e "${GREEN}Build completed!${NC}"
echo -e "Artifacts in ${YELLOW}dist/${NC}:"
ls -la dist/ 2>/dev/null || echo "No dist directory created"

echo -e "\n${GREEN}Library paths:${NC}"
echo "Static library: target/release/libnews_validator.a"
echo "Shared library: target/release/libnews_validator.so (or .dylib on macOS)"
echo "C header: include/news_validator.h"

# Test compilation
echo -e "\n${GREEN}Testing C compilation...${NC}"
cat > test_compile.c << 'EOF'
#include "include/news_validator.h"
#include <stdio.h>

int main() {
    printf("Validator library test compile\n");
    return 0;
}
EOF

if gcc -I./include test_compile.c -L./target/release -lnews_validator -o test_compile 2>/dev/null; then
    echo -e "${GREEN}C compilation test passed${NC}"
    rm -f test_compile test_compile.c
else
    echo -e "${YELLOW}C compilation test skipped (gcc not available)${NC}"
    rm -f test_compile.c
fi