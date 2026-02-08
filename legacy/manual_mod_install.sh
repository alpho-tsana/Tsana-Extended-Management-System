#!/bin/bash
# =============================================================================
# DayZ Manual Mod Installer
# Version: 0.6
# Author: Engineer Alpho (with assistance from Claude/Anthropic)
# License: GPL-3.0
# Repository: https://github.com/EngineerAlpho/dayz-mod-scripts
# =============================================================================
#
# Installs mods that fail Workshop downloads. Validates mod structure,
# copies keys, converts to lowercase, and updates server configuration.
#
# =============================================================================

# Colors for output (define if not already set)
if [ -z "$GREEN" ]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
fi

# Default paths (define if not already set)
if [ -z "$SERVER_MODS_DIR" ]; then
    SERVER_MODS_DIR="$HOME/serverfiles/mods"
fi

if [ -z "$LGSM_CONFIG" ]; then
    LGSM_CONFIG="$HOME/lgsm/config-lgsm/dayzserver/dayzserver.cfg"
fi

if [ -z "$KEYS_DIR" ]; then
    KEYS_DIR="$HOME/serverfiles/keys"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Manual Mod Installation v0.6${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Instructions:${NC}"
echo "1. Download the mod manually (from Steam Workshop browser or client)"
echo "2. Upload/copy the mod folder to: ${BLUE}$SERVER_MODS_DIR${NC}"
echo "3. Name it with @ prefix (e.g., @RaG_BaseItems)"
echo ""
echo -e "${YELLOW}Available mods in $SERVER_MODS_DIR:${NC}"
echo ""

# List existing mods in the directory
if [ -d "$SERVER_MODS_DIR" ]; then
    MOD_COUNT=0
    AVAILABLE_MODS=()
    
    while IFS= read -r mod_dir; do
        if [ -d "$mod_dir" ]; then
            mod_name=$(basename "$mod_dir")
            MOD_COUNT=$((MOD_COUNT + 1))
            AVAILABLE_MODS+=("$mod_name")
            echo -e "  $MOD_COUNT. ${YELLOW}$mod_name${NC}"
        fi
    done < <(find "$SERVER_MODS_DIR" -maxdepth 1 -type d -name "@*" | sort)
    
    if [ $MOD_COUNT -eq 0 ]; then
        echo -e "${YELLOW}  No mods found with @ prefix${NC}"
        echo ""
        echo -e "${RED}Please upload your mod to $SERVER_MODS_DIR first${NC}"
        echo "Example: $SERVER_MODS_DIR/@RaG_BaseItems"
        exit 1
    fi
else
    echo -e "${RED}Error: Mods directory not found: $SERVER_MODS_DIR${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Select a mod to install (or 'q' to quit):${NC}"
read -p "> " selection

if [[ "$selection" == "q" ]]; then
    exit 0
fi

# Validate selection
if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt "$MOD_COUNT" ]; then
    echo -e "${RED}Invalid selection${NC}"
    exit 1
fi

MOD_NAME="${AVAILABLE_MODS[$((selection-1))]}"
MOD_PATH="$SERVER_MODS_DIR/$MOD_NAME"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installing: $MOD_NAME${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Validation: Check if mod has proper structure
echo -e "${BLUE}Validating mod structure...${NC}"

VALIDATION_PASSED=true
VALIDATION_WARNINGS=()

# Check for addons folder
if [ ! -d "$MOD_PATH/addons" ] && [ ! -d "$MOD_PATH/Addons" ]; then
    VALIDATION_WARNINGS+=("${YELLOW}Warning: No 'addons' folder found${NC}")
    VALIDATION_PASSED=false
fi

# Check for at least one PBO file
PBO_COUNT=$(find "$MOD_PATH" -name "*.pbo" 2>/dev/null | wc -l)
if [ $PBO_COUNT -eq 0 ]; then
    VALIDATION_WARNINGS+=("${YELLOW}Warning: No .pbo files found${NC}")
    VALIDATION_PASSED=false
fi

# Check for mod.cpp (optional but recommended)
if [ ! -f "$MOD_PATH/mod.cpp" ]; then
    VALIDATION_WARNINGS+=("${YELLOW}Note: No mod.cpp found (optional)${NC}")
fi

if [ "$VALIDATION_PASSED" = false ]; then
    echo ""
    for warning in "${VALIDATION_WARNINGS[@]}"; do
        echo -e "$warning"
    done
    echo ""
    echo -e "${YELLOW}This mod may not be properly structured.${NC}"
    while true; do
        read -p "Continue anyway? (y/n): " continue_choice
        case "$continue_choice" in
            [Yy]* ) break;;
            [Nn]* ) exit 1;;
            * ) echo -e "${RED}Please answer y or n.${NC}";;
        esac
    done
else
    echo -e "${GREEN}✓ Mod structure validated${NC}"
    echo -e "  - Found addons folder"
    echo -e "  - Found $PBO_COUNT .pbo file(s)"
fi

# Copy keys
echo ""
echo -e "${BLUE}Copying mod keys...${NC}"

KEY_COPIED=false

# Check common key locations
for key_dir in "keys" "Keys" "key" "Key"; do
    KEY_SOURCE="$MOD_PATH/$key_dir"
    if [ -d "$KEY_SOURCE" ]; then
        KEY_FILES=$(find "$KEY_SOURCE" -name "*.bikey" 2>/dev/null)
        if [ -n "$KEY_FILES" ]; then
            while IFS= read -r key_file; do
                key_name=$(basename "$key_file")
                cp -v "$key_file" "$KEYS_DIR/" 2>/dev/null
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}✓ Copied: $key_name${NC}"
                    KEY_COPIED=true
                fi
            done <<< "$KEY_FILES"
        fi
    fi
done

if [ "$KEY_COPIED" = false ]; then
    echo -e "${YELLOW}No .bikey files found (some mods don't require keys)${NC}"
fi

# Convert to lowercase
echo ""
echo -e "${BLUE}Converting contents to lowercase...${NC}"

# Lowercase all files first
find "$MOD_PATH" -depth -type f | while read -r file; do
    dir=$(dirname "$file")
    filename=$(basename "$file")
    lowercase_filename=$(echo "$filename" | tr '[:upper:]' '[:lower:]')
    if [ "$filename" != "$lowercase_filename" ]; then
        mv "$file" "$dir/$lowercase_filename" 2>/dev/null
    fi
done

# Then lowercase all directories (except the root mod directory)
find "$MOD_PATH" -mindepth 1 -depth -type d | while read -r dir; do
    parent_dir=$(dirname "$dir")
    dirname_only=$(basename "$dir")
    lowercase_dir=$(echo "$dirname_only" | tr '[:upper:]' '[:lower:]')
    if [ "$dirname_only" != "$lowercase_dir" ]; then
        mv "$dir" "$parent_dir/$lowercase_dir" 2>/dev/null
    fi
done

echo -e "${GREEN}✓ Contents converted to lowercase${NC}"

# Update LinuxGSM config
echo ""
echo -e "${BLUE}Updating server configuration...${NC}"

if [ -f "$LGSM_CONFIG" ]; then
    # Check if mods parameter exists
    if grep -q "^mods=" "$LGSM_CONFIG"; then
        # Get current mods
        CURRENT_MODS_RAW=$(grep "^mods=" "$LGSM_CONFIG" | sed 's/^mods=//' | tr -d '"')
        CURRENT_MODS=$(echo "$CURRENT_MODS_RAW" | sed 's/\\;/;/g' | sed 's/mods\/@/@/g')
        
        # Check if mod already exists
        IFS=';' read -ra MOD_ARRAY <<< "$CURRENT_MODS"
        MOD_EXISTS=false
        
        for mod in "${MOD_ARRAY[@]}"; do
            if [ "$mod" = "$MOD_NAME" ]; then
                MOD_EXISTS=true
                break
            fi
        done
        
        if [ "$MOD_EXISTS" = true ]; then
            echo -e "${YELLOW}$MOD_NAME already in configuration${NC}"
        else
            # Add mod to list
            if [ -z "$CURRENT_MODS" ]; then
                NEW_MODS="mods/$MOD_NAME"
            else
                NEW_MODS=""
                for mod in "${MOD_ARRAY[@]}"; do
                    if [ -n "$mod" ]; then
                        if [ -z "$NEW_MODS" ]; then
                            NEW_MODS="mods/$mod"
                        else
                            NEW_MODS="$NEW_MODS\\\\;mods/$mod"
                        fi
                    fi
                done
                NEW_MODS="$NEW_MODS\\\\;mods/$MOD_NAME"
            fi
            
            sed -i 's|^mods=.*|mods="'"$NEW_MODS"'"|' "$LGSM_CONFIG"
            echo -e "${GREEN}✓ Added $MOD_NAME to server mods${NC}"
        fi
    else
        # Add mods parameter
        echo "mods=\"mods/$MOD_NAME\"" >> "$LGSM_CONFIG"
        echo -e "${GREEN}✓ Added mods parameter with $MOD_NAME${NC}"
    fi
else
    echo -e "${YELLOW}Warning: LinuxGSM config not found at $LGSM_CONFIG${NC}"
    echo -e "${YELLOW}You'll need to manually add the mod to your startup parameters${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Mod Details:${NC}"
echo -e "  Mod Name: ${YELLOW}$MOD_NAME${NC}"
echo -e "  Location: ${YELLOW}$MOD_PATH${NC}"
echo ""
echo -e "${YELLOW}Current mods in config:${NC}"
if [ -f "$LGSM_CONFIG" ]; then
    grep "^mods=" "$LGSM_CONFIG" | sed 's/^mods=//' | sed 's/\\;/\n/g' | sed 's/mods\//  @/g'
fi
echo ""

# Prompt to install another mod or exit
while true; do
    echo -e "${YELLOW}Would you like to install another mod? (y/n):${NC}"
    read -p "> " choice
    case "$choice" in
        [Yy]* )
            echo ""
            echo -e "${GREEN}========================================${NC}"
            # Re-run the parent script
            exec "$(dirname "$0")/download_workshop_mod.sh"
            ;;
        [Nn]* )
            echo ""
            echo -e "${GREEN}All done! Don't forget to restart your server.${NC}"
            exit 0
            ;;
        * )
            echo -e "${RED}Please answer y or n.${NC}"
            ;;
    esac
done
