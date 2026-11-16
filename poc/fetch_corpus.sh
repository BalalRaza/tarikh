#!/bin/bash
set -e

if [ ! -d "0325AH" ]; then
    echo "Cloning 0325AH repo (shallow)..."
    git clone --depth 1 https://github.com/OpenITI/0325AH.git
else
    echo "0325AH already cloned."
fi

echo ""
echo "Tabari Tarikh mARkdown files:"
find 0325AH/data -name "*Tabari*Tarikh*.mARkdown" -type f
