#!/usr/bin/env bash

cat << "EOF"
  __  __ _ _       _         ____        _   
 |  \/  (_) |_ ___| |__     | __ )  ___ | |_ 
 | |\/| | | __/ __| '_ \____|  _ \ / _ \| __|
 | |  | | | || (__| | | |____| |_) | (_) | |_ 
 |_|  |_|_|\__\___|_| |_|    |____/ \___/ \__|
         Milo Discord Fun Bot Installer       
--------------------------------------------------
EOF

GREEN='\033[1;92m'
YELLOW='\033[1;93m'
BLUE='\033[1;94m'
RED='\033[1;91m'
NC='\033[0m'

REPO_URL="https://github.com/msgaxzzz/Milo-discord-fun-bot.git"
DIR_NAME="Milo-discord-fun-bot"

if [ ! -d "$DIR_NAME" ]; then
    echo -e "${BLUE}Cloning repository from $REPO_URL...${NC}"
    git clone "$REPO_URL" || { echo -e "${RED}Failed to clone repository.${NC}"; exit 1; }
else
    echo -e "${YELLOW}Directory $DIR_NAME already exists, skipping clone.${NC}"
fi

cd "$DIR_NAME" || { echo -e "${RED}Cannot enter directory $DIR_NAME.${NC}"; exit 1; }

echo -e "${BLUE}Checking for compatible Python versions (>=3.7)...${NC}"
PYTHON_BIN=""

for PY in python3.11 python3.10 python3.9 python3.8 python3.7 python3; do
    if command -v $PY &> /dev/null; then
        VERSION=$($PY -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')")
        if (( $(echo "$VERSION >= 3.7" | bc -l) )); then
            PYTHON_BIN=$PY
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}No compatible Python (>=3.7) found. Please install Python 3.7 or higher.${NC}"
    exit 1
fi

echo -e "${GREEN}Found Python: $PYTHON_BIN${NC}"

echo -e "${BLUE}Checking for pip...${NC}"
if ! ($PYTHON_BIN -m pip --version &> /dev/null); then
    echo -e "${YELLOW}pip not found, installing pip...${NC}"
    $PYTHON_BIN -m ensurepip --upgrade
fi

echo -e "${BLUE}Installing dependencies from requirements.txt...${NC}"
$PYTHON_BIN -m pip install --upgrade pip
$PYTHON_BIN -m pip install -r requirements.txt

echo -e "${BLUE}Creating database directory...${NC}"
mkdir -p database

if [ -f config.json ]; then
    echo -e "${YELLOW}config.json exists, deleting to regenerate...${NC}"
    rm config.json
fi

echo -e "${BLUE}Configuration wizard:${NC}"

while true; do
    read -p "Enter Discord Bot Token (required): " DISCORD_TOKEN
    [[ -n "$DISCORD_TOKEN" ]] && break
    echo "Discord Token cannot be empty."
done

read -p "Enter OpenAI API Key (optional): " OPENAI_KEY

if [[ -n "$OPENAI_KEY" ]]; then
    read -p "Enter OpenAI API Base URL (default https://api.openai.com/v1): " OPENAI_API_BASE
    OPENAI_API_BASE=${OPENAI_API_BASE:-https://api.openai.com/v1}

    read -p "Allow user-provided OpenAI Keys? (true/false, default true): " ALLOW_USER_KEYS
    if [[ ! "$ALLOW_USER_KEYS" =~ ^(true|false)$ ]]; then
        ALLOW_USER_KEYS=true
    fi

    read -p "Enter default chat model (default gpt-4o-mini): " DEFAULT_CHAT_MODEL
    DEFAULT_CHAT_MODEL=${DEFAULT_CHAT_MODEL:-gpt-4o-mini}

    read -p "Enter allowed chat models, comma separated (default gpt-4o-mini,gpt-4o): " ALLOWED_CHAT_MODELS_INPUT
    if [[ -z "$ALLOWED_CHAT_MODELS_INPUT" ]]; then
        ALLOWED_CHAT_MODELS='["gpt-4o-mini", "gpt-4o"]'
    else
        IFS=',' read -ra MODELS_ARR <<< "$ALLOWED_CHAT_MODELS_INPUT"
        ALLOWED_CHAT_MODELS=$(printf '"%s",' "${MODELS_ARR[@]}")
        ALLOWED_CHAT_MODELS="[${ALLOWED_CHAT_MODELS%,}]"
    fi
else
    OPENAI_API_BASE=""
    ALLOW_USER_KEYS=false
    DEFAULT_CHAT_MODEL=""
    ALLOWED_CHAT_MODELS="[]"
fi

read -p "Enter Google API Key (optional): " GOOGLE_API_KEY
read -p "Enter Google CSE ID (optional): " GOOGLE_CSE_ID

cat > config.json <<EOF
{
  "DISCORD_TOKEN": "$DISCORD_TOKEN",
  "OPENAI_API_KEY": "$OPENAI_KEY",
  "OPENAI_API_BASE": "$OPENAI_API_BASE",
  "ALLOW_USER_KEYS": $ALLOW_USER_KEYS,
  "DEFAULT_CHAT_MODEL": "$DEFAULT_CHAT_MODEL",
  "ALLOWED_CHAT_MODELS": $ALLOWED_CHAT_MODELS,
  "GOOGLE_API_KEY": "$GOOGLE_API_KEY",
  "GOOGLE_CSE_ID": "$GOOGLE_CSE_ID"
}
EOF

echo -e "${GREEN}config.json created successfully.${NC}"
echo -e "${GREEN}Milo Bot installation completed!${NC}"
echo -e "${YELLOW}Please verify config.json and run:${NC}"
echo -e "  ${BLUE}$PYTHON_BIN main.py${NC}"
echo -e "${BLUE}Update log: https://github.com/msgaxzzz/Milo-discord-fun-bot/blob/main/CHANGELOG.md${NC}"
