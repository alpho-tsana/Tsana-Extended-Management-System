#!/bin/bash
# =============================================================================
# DayZ Mod Load Order Manager
# Version: 0.6
# Author: alpho-tsana (with assistance from Claude/Anthropic)
# License: GPL-3.0
# Repository: https://github.com/alpho-tsana/dayz-mod-scripts
# =============================================================================
#
# Interactive tool for managing mod load order. Move mods up/down or to
# specific positions to ensure proper loading sequence.
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
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DayZ Mod Load Order Manager v0.6${NC}"
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

if [ -z "$CURRENT_MODS" ]; then
    echo -e "${YELLOW}No mods configured yet${NC}"
    exit 0
fi

# Convert to array
IFS=';' read -ra MOD_ARRAY <<< "$CURRENT_MODS"

echo -e "${CYAN}Load Order Best Practices:${NC}"
echo -e "${YELLOW}1.${NC} Map mods (like @Banov) should be FIRST"
echo -e "${YELLOW}2.${NC} Framework mods (@CF, @DabsFramework) load early"
echo -e "${YELLOW}3.${NC} @DayZ-Expansion-Core before other Expansion mods"
echo -e "${YELLOW}4.${NC} Dependency mods before mods that require them"
echo ""

display_mods() {
    echo -e "${BLUE}Current Load Order:${NC}"
    for i in "${!MOD_ARRAY[@]}"; do
        if [ -n "${MOD_ARRAY[$i]}" ]; then
            echo -e "  $((i+1)). ${YELLOW}${MOD_ARRAY[$i]}${NC}"
        fi
    done
    echo ""
}

while true; do
    display_mods
    
    echo -e "${YELLOW}Options:${NC}"
    echo "  1. Move a mod up (load earlier)"
    echo "  2. Move a mod down (load later)"
    echo "  3. Move a mod to specific position"
    echo "  4. Save and exit"
    echo "  5. Cancel (don't save)"
    echo ""
    read -p "Choose option (1-5): " choice
    
    case $choice in
        1)
            echo ""
            read -p "Enter the number of the mod to move UP: " mod_num
            
            if ! [[ "$mod_num" =~ ^[0-9]+$ ]] || [ "$mod_num" -lt 1 ] || [ "$mod_num" -gt "${#MOD_ARRAY[@]}" ]; then
                echo -e "${RED}Invalid selection${NC}"
                echo ""
                continue
            fi
            
            idx=$((mod_num-1))
            
            if [ $idx -eq 0 ]; then
                echo -e "${YELLOW}Already at the top!${NC}"
                echo ""
                continue
            fi
            
            # Swap with previous
            temp="${MOD_ARRAY[$idx]}"
            MOD_ARRAY[$idx]="${MOD_ARRAY[$((idx-1))]}"
            MOD_ARRAY[$((idx-1))]="$temp"
            
            echo -e "${GREEN}✓ Moved ${temp} up${NC}"
            echo ""
            ;;
        2)
            echo ""
            read -p "Enter the number of the mod to move DOWN: " mod_num
            
            if ! [[ "$mod_num" =~ ^[0-9]+$ ]] || [ "$mod_num" -lt 1 ] || [ "$mod_num" -gt "${#MOD_ARRAY[@]}" ]; then
                echo -e "${RED}Invalid selection${NC}"
                echo ""
                continue
            fi
            
            idx=$((mod_num-1))
            
            if [ $idx -eq $((${#MOD_ARRAY[@]}-1)) ]; then
                echo -e "${YELLOW}Already at the bottom!${NC}"
                echo ""
                continue
            fi
            
            # Swap with next
            temp="${MOD_ARRAY[$idx]}"
            MOD_ARRAY[$idx]="${MOD_ARRAY[$((idx+1))]}"
            MOD_ARRAY[$((idx+1))]="$temp"
            
            echo -e "${GREEN}✓ Moved ${temp} down${NC}"
            echo ""
            ;;
        3)
            echo ""
            read -p "Enter the number of the mod to move: " mod_num
            
            if ! [[ "$mod_num" =~ ^[0-9]+$ ]] || [ "$mod_num" -lt 1 ] || [ "$mod_num" -gt "${#MOD_ARRAY[@]}" ]; then
                echo -e "${RED}Invalid selection${NC}"
                echo ""
                continue
            fi
            
            read -p "Enter the new position (1-${#MOD_ARRAY[@]}): " new_pos
            
            if ! [[ "$new_pos" =~ ^[0-9]+$ ]] || [ "$new_pos" -lt 1 ] || [ "$new_pos" -gt "${#MOD_ARRAY[@]}" ]; then
                echo -e "${RED}Invalid position${NC}"
                echo ""
                continue
            fi
            
            old_idx=$((mod_num-1))
            new_idx=$((new_pos-1))
            
            if [ $old_idx -eq $new_idx ]; then
                echo -e "${YELLOW}Same position!${NC}"
                echo ""
                continue
            fi
            
            # Store the mod to move
            mod_to_move="${MOD_ARRAY[$old_idx]}"
            
            # Remove from old position
            unset 'MOD_ARRAY[$old_idx]'
            MOD_ARRAY=("${MOD_ARRAY[@]}")
            
            # Insert at new position
            if [ $new_idx -eq 0 ]; then
                MOD_ARRAY=("$mod_to_move" "${MOD_ARRAY[@]}")
            elif [ $new_idx -ge ${#MOD_ARRAY[@]} ]; then
                MOD_ARRAY+=("$mod_to_move")
            else
                MOD_ARRAY=("${MOD_ARRAY[@]:0:$new_idx}" "$mod_to_move" "${MOD_ARRAY[@]:$new_idx}")
            fi
            
            echo -e "${GREEN}✓ Moved ${mod_to_move} to position $new_pos${NC}"
            echo ""
            ;;
        4)
            # Save
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
            
            sed -i 's|^mods=.*|mods="'"$NEW_MODS"'"|' "$LGSM_CONFIG"
            
            echo ""
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}✓ Load order saved!${NC}"
            echo -e "${GREEN}========================================${NC}"
            echo ""
            echo -e "${BLUE}Final Load Order:${NC}"
            for i in "${!MOD_ARRAY[@]}"; do
                if [ -n "${MOD_ARRAY[$i]}" ]; then
                    echo -e "  $((i+1)). ${YELLOW}${MOD_ARRAY[$i]}${NC}"
                fi
            done
            echo ""
            echo -e "${CYAN}Remember to restart your server for changes to take effect!${NC}"
            exit 0
            ;;
        5)
            echo ""
            echo -e "${YELLOW}Cancelled - no changes saved${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            echo ""
            ;;
    esac
done
