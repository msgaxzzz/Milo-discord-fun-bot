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

PYTHON_OPTIONS=()
PYTHON_CMDS=()
PYTHON_VERSIONS=()

if command -v python3 &> /dev/null; then
    PYTHON_OPTIONS+=("python3")
    PYTHON_CMDS+=("python3")
    PYTHON_VERSIONS+=("$(python3 --version 2>&1)")
fi

if command -v python &> /dev/null; then
    PYTHON_OPTIONS+=("python")
    PYTHON_CMDS+=("python")
    PYTHON_VERSIONS+=("$(python --version 2>&1)")
fi

if [ ${#PYTHON_OPTIONS[@]} -eq 0 ]; then
    echo -e "${YELLOW}Error: Neither python3 nor python is installed.${NC}"
    echo "Please install Python 3 (recommended) or Python, then run this script again."
    exit 1
fi

echo -e "\nAvailable Python versions found:"
for i in "${!PYTHON_OPTIONS[@]}"; do
    echo "  [$(($i+1))] ${PYTHON_OPTIONS[$i]} (${PYTHON_VERSIONS[$i]})"
done

SELECTED_PYTHON=""
SELECTED_PIP=""
DEFAULT_CHOICE=1

while true; do
    echo -ne "${YELLOW}Please choose which Python version to use (${PYTHON_OPTIONS[0]} is recommended, default is $DEFAULT_CHOICE): ${NC}"
    read -r choice
    choice=$(echo "$choice" | tr -d '[:space:]')

    if [[ -z "$choice" ]]; then
        choice="$DEFAULT_CHOICE"
    fi

    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#PYTHON_OPTIONS[@]} ]; then
        SELECTED_PYTHON=${PYTHON_CMDS[$(($choice-1))]}
        
        if [ "$SELECTED_PYTHON" == "python3" ]; then
            if command -v pip3 &> /dev/null; then
                SELECTED_PIP="pip3"
            else
                SELECTED_PIP="$SELECTED_PYTHON -m pip"
            fi
        elif [ "$SELECTED_PYTHON" == "python" ]; then
            if command -v pip &> /dev/null; then
                SELECTED_PIP="pip"
            else
                SELECTED_PIP="$SELECTED_PYTHON -m pip"
            fi
        fi

        if ! command -v $SELECTED_PIP &> /dev/null && ! ($SELECTED_PYTHON -m pip --version &> /dev/null); then
            echo -e "${YELLOW}Warning: Pip for '$SELECTED_PYTHON' was not found or is not working. Trying '$SELECTED_PYTHON -m pip'.${NC}"
            SELECTED_PIP="$SELECTED_PYTHON -m pip"
            if ! ($SELECTED_PYTHON -m pip --version &> /dev/null); then
                 echo -e "${YELLOW}Error: Neither '$SELECTED_PIP' nor '$SELECTED_PYTHON -m pip' works. Please install Pip for '$SELECTED_PYTHON'.${NC}"
                 exit 1
            fi
        fi

        break
    else
        echo -e "${YELLOW}Invalid choice: '$choice'. Please enter a number from the list.${NC}"
    fi
done

echo -e "${GREEN}You chose to use: '$SELECTED_PYTHON' (Pip command: '$SELECTED_PIP')${NC}"

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
$SELECTED_PIP install -r requirements.txt
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
echo -e "   ${BLUE}cd $REPO_DIR${NC}"
echo "4. Then start the bot:"
echo -e "   ${BLUE}$SELECTED_PYTHON main.py${NC}"
echo ""
