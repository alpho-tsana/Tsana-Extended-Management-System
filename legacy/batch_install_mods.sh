#!/bin/bash
# =============================================================================
# DayZ Batch Mod Installer
# Version: 0.6
# Author: alpho-tsana (with assistance from Claude/Anthropic)
# License: GPL-3.0
# Repository: https://github.com/alpho-tsana/dayz-mod-scripts
# =============================================================================
#
# Installs multiple mods from a list file. Validates Workshop IDs,
# downloads all mods in a single SteamCMD session, and automatically
# cleans up Workshop files after installation.
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

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DayZ Batch Mod Installer v0.6${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if SteamCMD exists
if [ ! -f "$STEAMCMD_PATH" ]; then
    echo -e "${RED}Error: SteamCMD not found at $STEAMCMD_PATH${NC}"
    exit 1
fi

# Create mods directory if it doesn't exist
mkdir -p "$SERVER_MODS_DIR"

# Check for mod list file argument
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <mod_list_file>${NC}"
    echo ""
    echo -e "${CYAN}Create a text file with one mod per line in this format:${NC}"
    echo -e "${YELLOW}ModName - https://steamcommunity.com/sharedfiles/filedetails/?id=XXXXXXXXX${NC}"
    echo ""
    echo -e "${CYAN}Example:${NC}"
    echo -e "Banov - https://steamcommunity.com/sharedfiles/filedetails/?id=2415195639"
    echo -e "DabsFramework - https://steamcommunity.com/sharedfiles/filedetails/?id=2545327648"
    echo ""
    exit 1
fi

MOD_LIST_FILE="$1"

if [ ! -f "$MOD_LIST_FILE" ]; then
    echo -e "${RED}Error: Mod list file not found: $MOD_LIST_FILE${NC}"
    exit 1
fi

# Count total mods
total_mods=$(grep -c "https://steamcommunity.com" "$MOD_LIST_FILE")

echo -e "${CYAN}Found $total_mods mod(s) in list${NC}"
echo ""

# Ask for confirmation
echo -e "${YELLOW}This will download and install $total_mods mods. Continue? (y/n):${NC}"
read -p "> " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cancelled${NC}"
    exit 0
fi

echo ""

# First pass: Build list of mods and create SteamCMD script
echo -e "${BLUE}Parsing mod list and building download script...${NC}"
declare -a MOD_NAMES=()
declare -a WORKSHOP_IDS=()

while IFS= read -r line; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    
    # Extract mod name and workshop ID
    if [[ "$line" =~ ^(.+)[[:space:]]*-[[:space:]]*https://steamcommunity.com/sharedfiles/filedetails/\?id=([0-9]+) ]]; then
        MOD_NAME="${BASH_REMATCH[1]}"
        WORKSHOP_ID="${BASH_REMATCH[2]}"
        
        # Trim whitespace
        MOD_NAME=$(echo "$MOD_NAME" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # Add @ prefix if not present
        if [[ ! "$MOD_NAME" =~ ^@ ]]; then
            MOD_NAME="@$MOD_NAME"
        fi
        
        # Remove spaces from mod name
        MOD_NAME=$(echo "$MOD_NAME" | tr -d ' ')
        
        MOD_NAMES+=("$MOD_NAME")
        WORKSHOP_IDS+=("$WORKSHOP_ID")
    fi
done < "$MOD_LIST_FILE"

# Build SteamCMD script
STEAMCMD_SCRIPT="/tmp/dayz_batch_download_$$.txt"
echo "login $STEAM_USER $STEAM_PASS" > "$STEAMCMD_SCRIPT"
for workshop_id in "${WORKSHOP_IDS[@]}"; do
    echo "workshop_download_item $DAYZ_APP_ID $workshop_id" >> "$STEAMCMD_SCRIPT"
done
echo "quit" >> "$STEAMCMD_SCRIPT"

echo -e "${GREEN}✓ Found ${#MOD_NAMES[@]} mods to download${NC}"
echo ""

# Validate Workshop IDs
echo -e "${BLUE}Validating Workshop IDs...${NC}"
INVALID_IDS=()

for i in "${!WORKSHOP_IDS[@]}"; do
    workshop_id="${WORKSHOP_IDS[$i]}"
    mod_name="${MOD_NAMES[$i]}"
    
    WORKSHOP_URL="https://steamcommunity.com/sharedfiles/filedetails/?id=$workshop_id"
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -L "$WORKSHOP_URL" 2>/dev/null)
    
    if [ "$HTTP_STATUS" -eq 200 ]; then
        echo -e "  ${GREEN}✓${NC} $mod_name (ID: $workshop_id)"
    elif [ "$HTTP_STATUS" -eq 404 ]; then
        echo -e "  ${RED}✗${NC} $mod_name (ID: $workshop_id) - NOT FOUND"
        INVALID_IDS+=("$mod_name")
    else
        echo -e "  ${YELLOW}?${NC} $mod_name (ID: $workshop_id) - Could not validate (HTTP $HTTP_STATUS)"
    fi
done

if [ ${#INVALID_IDS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}The following mods have invalid Workshop IDs:${NC}"
    for mod in "${INVALID_IDS[@]}"; do
        echo -e "  ${RED}✗${NC} $mod"
    done
    echo ""
    while true; do
        read -p "Continue anyway? (y/n): " continue_choice
        case "$continue_choice" in
            [Yy]* ) break;;
            [Nn]* ) exit 1;;
            * ) echo -e "${RED}Please answer y or n.${NC}";;
        esac
    done
fi

echo ""

# Download all mods in one SteamCMD session
echo -e "${BLUE}Downloading all mods in a single SteamCMD session...${NC}"
echo -e "${YELLOW}This may take a while...${NC}"
echo ""

$STEAMCMD_PATH +runscript "$STEAMCMD_SCRIPT"
DOWNLOAD_RESULT=$?

# Clean up script file
rm -f "$STEAMCMD_SCRIPT"

if [ $DOWNLOAD_RESULT -ne 0 ]; then
    echo -e "${RED}SteamCMD download session failed${NC}"
    echo -e "${YELLOW}Some or all mods may not have downloaded. Continuing with installation...${NC}"
    echo ""
fi

# Process each mod - copy, configure, etc.
current=0
failed_mods=()
successful_mods=()

for i in "${!MOD_NAMES[@]}"; do
    MOD_NAME="${MOD_NAMES[$i]}"
    WORKSHOP_ID="${WORKSHOP_IDS[$i]}"
    
    current=$((current + 1))
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}[$current/${#MOD_NAMES[@]}] Processing: $MOD_NAME${NC}"
    echo -e "${GREEN}Workshop ID: $WORKSHOP_ID${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
        
        MOD_WORKSHOP_PATH="$WORKSHOP_DIR/$WORKSHOP_ID"
        MOD_DEST_PATH="$SERVER_MODS_DIR/$MOD_NAME"
        
        # Copy mod directory
        echo -e "${BLUE}Copying mod files...${NC}"
        if [ -d "$MOD_DEST_PATH" ]; then
            echo -e "${YELLOW}Removing old version...${NC}"
            rm -rf "$MOD_DEST_PATH"
        fi
        
        cp -r "$MOD_WORKSHOP_PATH" "$MOD_DEST_PATH"
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}✗ Failed to copy files for $MOD_NAME${NC}"
            failed_mods+=("$MOD_NAME (ID: $WORKSHOP_ID)")
            echo ""
            continue
        fi
        
        echo -e "${GREEN}✓ Files copied${NC}"
        
        # Copy keys
        echo -e "${BLUE}Copying mod keys...${NC}"
        KEY_SOURCE="$MOD_DEST_PATH/keys"
        KEY_SOURCE_ALT="$MOD_DEST_PATH/Keys"
        
        if [ -d "$KEY_SOURCE" ]; then
            cp -v "$KEY_SOURCE"/*.bikey "$KEYS_DIR/" 2>/dev/null && echo -e "${GREEN}✓ Keys copied${NC}" || echo -e "${YELLOW}No .bikey files found${NC}"
        elif [ -d "$KEY_SOURCE_ALT" ]; then
            cp -v "$KEY_SOURCE_ALT"/*.bikey "$KEYS_DIR/" 2>/dev/null && echo -e "${GREEN}✓ Keys copied${NC}" || echo -e "${YELLOW}No .bikey files found${NC}"
        else
            echo -e "${YELLOW}No keys directory found${NC}"
        fi
        
        # Convert contents to lowercase
        echo -e "${BLUE}Converting contents to lowercase...${NC}"
        
        # Lowercase all files first
        find "$MOD_DEST_PATH" -depth -type f | while read -r file; do
            dir=$(dirname "$file")
            filename=$(basename "$file")
            lowercase_filename=$(echo "$filename" | tr '[:upper:]' '[:lower:]')
            if [ "$filename" != "$lowercase_filename" ]; then
                mv "$file" "$dir/$lowercase_filename" 2>/dev/null
            fi
        done
        
        # Then lowercase all directories (except the root mod directory)
        find "$MOD_DEST_PATH" -mindepth 1 -depth -type d | while read -r dir; do
            parent_dir=$(dirname "$dir")
            dirname_only=$(basename "$dir")
            lowercase_dir=$(echo "$dirname_only" | tr '[:upper:]' '[:lower:]')
            if [ "$dirname_only" != "$lowercase_dir" ]; then
                mv "$dir" "$parent_dir/$lowercase_dir" 2>/dev/null
            fi
        done
        
        echo -e "${GREEN}✓ Contents converted to lowercase${NC}"
        
        # Clean up Workshop files to save disk space
        echo -e "${BLUE}Cleaning up Workshop files...${NC}"
        rm -rf "$MOD_WORKSHOP_PATH"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Workshop files cleaned up${NC}"
        else
            echo -e "${YELLOW}Warning: Could not clean up Workshop files${NC}"
        fi
        
        # Save mod mapping
        echo -e "${BLUE}Saving mod mapping...${NC}"
        if [ -f "$MOD_MAPPING_FILE" ]; then
            sed -i "/^$WORKSHOP_ID:/d" "$MOD_MAPPING_FILE"
        fi
        echo "$WORKSHOP_ID:$MOD_NAME" >> "$MOD_MAPPING_FILE"
        echo -e "${GREEN}✓ Mod mapping saved${NC}"
        
        # Update LinuxGSM config
        echo -e "${BLUE}Updating server configuration...${NC}"
        
        if [ -f "$LGSM_CONFIG" ]; then
            if grep -q "^mods=" "$LGSM_CONFIG"; then
                # Get current mods - convert escaped semicolons to regular semicolons for splitting
                CURRENT_MODS_RAW=$(grep "^mods=" "$LGSM_CONFIG" | sed 's/^mods=//' | tr -d '"')
                
                # Replace \; with regular ; for IFS splitting, and remove mods/ prefix
                CURRENT_MODS=$(echo "$CURRENT_MODS_RAW" | sed 's/\\;/;/g' | sed 's/mods\/@/@/g')
                
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
                    echo -e "${GREEN}✓ Added to server config${NC}"
                fi
            else
                echo "mods=\"mods/$MOD_NAME\"" >> "$LGSM_CONFIG"
                echo -e "${GREEN}✓ Added to server config${NC}"
            fi
        fi
        
        echo -e "${GREEN}✓ $MOD_NAME installed successfully!${NC}"
        successful_mods+=("$MOD_NAME")
        echo ""
done

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Summary:${NC}"
echo -e "  Total mods: ${YELLOW}${#MOD_NAMES[@]}${NC}"
echo -e "  Successful: ${GREEN}${#successful_mods[@]}${NC}"
echo -e "  Failed: ${RED}${#failed_mods[@]}${NC}"
echo ""

if [ ${#failed_mods[@]} -gt 0 ]; then
    echo -e "${RED}Failed mods:${NC}"
    for mod in "${failed_mods[@]}"; do
        echo -e "  ${RED}✗${NC} $mod"
    done
    echo ""
fi

echo -e "${YELLOW}Current mod load order:${NC}"
if [ -f "$LGSM_CONFIG" ]; then
    grep "^mods=" "$LGSM_CONFIG" | sed 's/^mods=//' | sed 's/\\;/\n/g' | sed 's/mods\//  /g'
fi
echo ""

echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Use ${YELLOW}./reorder_mods.sh${NC} to adjust load order if needed"
echo -e "  2. Restart your server: ${YELLOW}./dayzserver restart${NC}"
echo ""
