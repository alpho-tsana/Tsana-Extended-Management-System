#!/bin/bash
# =============================================================================
# DayZ Server Mod Management Configuration
# Version: 0.6
# Author: Engineer Alpho (with assistance from Claude/Anthropic)
# License: GPL-3.0
# Repository: https://github.com/EngineerAlpho/dayz-mod-scripts
# =============================================================================
# 
# This file contains paths and credentials used by all scripts
# Edit this file once and all scripts will use your settings
#
# =============================================================================

# ============================================
# STEAM CREDENTIALS
# ============================================
STEAM_USER="hasq2026"
STEAM_PASS="SolentSiteContact1!"
# Note: If you have Steam Guard, you'll need to enter the code manually on first run

# ============================================
# SERVER PATHS
# ============================================
# Adjust these if your server is in a different location
# Use absolute paths or $HOME for home directory
SERVER_BASE_DIR="$HOME"
SERVER_FILES_DIR="$SERVER_BASE_DIR/serverfiles"
SERVER_MODS_DIR="$SERVER_FILES_DIR/mods"
KEYS_DIR="$SERVER_FILES_DIR/keys"
LGSM_CONFIG="$SERVER_BASE_DIR/lgsm/config-lgsm/dayzserver/dayzserver.cfg"

# ============================================
# STEAMCMD PATHS
# ============================================
STEAMCMD_PATH="$HOME/.steam/steamcmd/steamcmd.sh"
WORKSHOP_DIR="$HOME/.local/share/Steam/steamapps/workshop/content/221100"

# ============================================
# MOD MANAGEMENT FILES
# ============================================
MOD_MAPPING_FILE="$SERVER_BASE_DIR/.dayz_mod_mapping"

# ============================================
# DayZ App ID (Don't change this)
# ============================================
DAYZ_APP_ID=221100
