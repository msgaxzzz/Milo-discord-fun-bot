#!/bin/bash

set -e

GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'

REPO_URL="https://github.com/msgaxzzz/Milo-discord-fun-bot.git"
REPO_DIR="Milo-discord-fun-bot"

echo -e "${BLUE}--- Starting Milo Bot Installation ---${NC}"

echo -e "\nStep 1: Checking for required tools (Git, Python)..."

if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}Error: git is not installed.${NC}"
    echo "Please install git (e.g., 'sudo apt install git' or 'sudo yum install git') and run this script again."
    exit 1
fi
echo -e "${GREEN}Git is installed.${NC}"

HAS_PYTHON3=false
HAS_PYTHON=false
if command -v python3 &> /dev/null; then
    HAS_PYTHON3=true
fi
if command -v python &> /dev/null; then
    HAS_PYTHON=true
fi

if [ "$HAS_PYTHON3" = false ] && [ "$HAS_PYTHON" = false ]; then
    echo -e "${YELLOW}Error: Neither python3 nor python is installed.${NC}"
    echo "Please install Python 3 and run this script again."
    exit 1
fi

echo -e "\nAvailable Python versions:"
if [ "$HAS_PYTHON3" = true ]; then
    echo " [1] python3 ($(python3 --version))"
fi
if [ "$HAS_PYTHON" = true ]; then
    echo " [2] python ($(python --version))"
fi

while true; do
    echo -ne "${YELLOW}Choose Python version to use (1 or 2): ${NC}"
    read -r choice
    if [ "$choice" = "1" ] && [ "$HAS_PYTHON3" = true ]; then
        PYTHON_CMD="python3"
        break
    elif [ "$choice" = "2" ] && [ "$HAS_PYTHON" = true ]; then
        PYTHON_CMD="python"
        break
    else
        echo -e "${YELLOW}Invalid choice. Please select a valid option.${NC}"
    fi
done

echo -e "${GREEN}You chose to use: '$PYTHON_CMD'${NC}"

echo -e "\nStep 2: Cloning the Milo Bot repository..."
if [ -d "$REPO_DIR" ]; then
    echo -e "${YELLOW}Directory '$REPO_DIR' already exists. Skipping clone.${NC}"
else
    git clone "$REPO_URL"
    echo -e "${GREEN}Repository cloned successfully.${NC}"
fi

cd "$REPO_DIR"
echo -e "\nEntered project directory: $(pwd)"

echo -e "\nStep 3: Installing Python libraries from requirements.txt..."
$PYTHON_CMD -m pip install -r requirements.txt
echo -e "${GREEN}Python libraries installed successfully.${NC}"

echo -e "\nStep 4: Setting up 'database' directory..."
if [ ! -d "database" ]; then
    mkdir database
    echo -e "${GREEN}'database' directory created.${NC}"
else
    echo -e "${YELLOW}'database' directory already exists. Skipping.${NC}"
fi

echo -e "\nStep 5: Creating 'config.json' template..."
if [ ! -f "config.json" ]; then
    cat << EOF > config.json
{
  "DISCORD_TOKEN": "YOUR_DISCORD_BOT_TOKEN_HERE",
  "OPENAI_API_KEY": "YOUR_OPENAI_API_KEY_HERE (OPTIONAL)",
  "OPENAI_API_BASE": "https://api.openai.com/v1",
  "ALLOW_USER_KEYS": true,
  "DEFAULT_CHAT_MODEL": "gpt-4o-mini",
  "ALLOWED_CHAT_MODELS": [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo"
  ],
  "GOOGLE_API_KEY": "YOUR_GOOGLE_API_KEY_HERE (OPTIONAL)",
  "GOOGLE_CSE_ID": "YOUR_GOOGLE_CSE_ID_HERE (OPTIONAL)"
}
EOF
    echo -e "${GREEN}'config.json' template created.${NC}"
else
    echo -e "${YELLOW}'config.json' already exists. Skipping template creation.${NC}"
fi

echo -e "\n${GREEN}--- Milo Bot Installation Complete! ---${NC}"
echo ""
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo "1. Your project is ready in the '${GREEN}$REPO_DIR${NC}' directory."
echo "2. Edit the '${GREEN}config.json${NC}' file inside that directory and fill in your API keys (at least DISCORD_TOKEN)."
echo "3. To run the bot, first enter the directory:"
echo -e "   ${BLUE}cd $(basename $PWD)${NC}"
echo "4. Then start the bot:"
echo -e "   ${BLUE}$PYTHON_CMD main.py${NC}"
echo ""
