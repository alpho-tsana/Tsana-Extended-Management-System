#!/bin/bash
# =============================================================================
# DayZ Mods Config Cleanup Utility
# Version: 0.6
# Author: alpho-tsana (with assistance from Claude/Anthropic)
# License: GPL-3.0
# Repository: https://github.com/alpho-tsana/dayz-mod-scripts
# =============================================================================
#
# Manages the mods list in your LinuxGSM config. Remove individual mods
# or clear all mods from your server configuration.
#
# =============================================================================

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    source "$SCRIPT_DIR/config.sh"
else
    echo "Error: config.sh not found!"
    echo "Please ensure config.sh is in the same directory as this script"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DayZ Mods Config Cleanup v0.6${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ ! -f "$LGSM_CONFIG" ]; then
    echo -e "${RED}Error: Config file not found at $LGSM_CONFIG${NC}"
    exit 1
fi

# Get current mods
if ! grep -q "^mods=" "$LGSM_CONFIG"; then
    echo -e "${YELLOW}No mods configured yet${NC}"
    exit 0
fi

# Get current mods - convert escaped semicolons to regular semicolons for splitting
CURRENT_MODS_RAW=$(grep "^mods=" "$LGSM_CONFIG" | sed 's/^mods=//' | tr -d '"')

# Replace \; with regular ; for IFS splitting, and remove mods/ prefix  
CURRENT_MODS=$(echo "$CURRENT_MODS_RAW" | sed 's/\\;/;/g' | sed 's/mods\/@/@/g')

echo -e "${BLUE}Current mods in config:${NC}"
echo ""

# Convert to array and display with numbers
IFS=';' read -ra MOD_ARRAY <<< "$CURRENT_MODS"
for i in "${!MOD_ARRAY[@]}"; do
    if [ -n "${MOD_ARRAY[$i]}" ]; then
        echo -e "  $((i+1)). ${YELLOW}${MOD_ARRAY[$i]}${NC}"
    fi
done

echo ""
echo -e "${YELLOW}Options:${NC}"
echo "  1. Remove a specific mod"
echo "  2. Clear all mods"
echo "  3. Exit"
echo ""
read -p "Choose option (1-3): " choice

case $choice in
    1)
        echo ""
        read -p "Enter the number of the mod to remove: " mod_num
        
        if ! [[ "$mod_num" =~ ^[0-9]+$ ]] || [ "$mod_num" -lt 1 ] || [ "$mod_num" -gt "${#MOD_ARRAY[@]}" ]; then
            echo -e "${RED}Invalid selection${NC}"
            exit 1
        fi
        
        # Remove the selected mod
        MOD_TO_REMOVE="${MOD_ARRAY[$((mod_num-1))]}"
        NEW_MODS=""
        
        for mod in "${MOD_ARRAY[@]}"; do
            if [ "$mod" != "$MOD_TO_REMOVE" ] && [ -n "$mod" ]; then
                if [ -z "$NEW_MODS" ]; then
                    NEW_MODS="mods/$mod"
                else
                    NEW_MODS="$NEW_MODS\\\\;mods/$mod"
                fi
            fi
        done
        
        sed -i 's|^mods=.*|mods="'"$NEW_MODS"'"|' "$LGSM_CONFIG"
        echo ""
        echo -e "${GREEN}✓ Removed $MOD_TO_REMOVE${NC}"
        echo ""
        echo -e "${BLUE}Updated mods list:${NC}"
        grep "^mods=" "$LGSM_CONFIG" | sed 's/^mods=//' | sed 's/\\;/\n/g' | sed 's/mods\//  /g'
        ;;
    2)
        echo ""
        read -p "Are you sure you want to remove ALL mods? (y/n): " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            sed -i 's|^mods=.*|mods=""|' "$LGSM_CONFIG"
            echo ""
            echo -e "${GREEN}✓ Cleared all mods from config${NC}"
        else
            echo -e "${YELLOW}Cancelled${NC}"
        fi
        ;;
    3)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac
