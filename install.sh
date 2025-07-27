#!/usr/bin/env bash

# Milo Discord Fun Bot - Installer v1.2.0
# MIT Licensed - https://github.com/msgaxzzz/Milo-Discord-fun-bot

# ---------------------- ASCII LOGO ----------------------
cat << "EOF"
  __  __ _ _       _         ____        _   
 |  \/  (_) |_ ___| |__     | __ )  ___ | |_ 
 | |\/| | | __/ __| '_ \____|  _ \ / _ \| __|
 | |  | | | || (__| | | |____| |_) | (_) | |_ 
 |_|  |_|_|\__\___|_| |_|    |____/ \___/ \__|
         Milo Discord Fun Bot Installer       
--------------------------------------------------
EOF

# ---------------------- Color Config ----------------------
GREEN='\033[1;92m'
YELLOW='\033[1;93m'
BLUE='\033[1;94m'
RED='\033[1;91m'
NC='\033[0m'

# ---------------------- Clone Repo ----------------------
REPO_URL="https://github.com/msgaxzzz/Milo-discord-fun-bot.git"
DIR_NAME="Milo-discord-fun-bot"

if [ ! -d "$DIR_NAME" ]; then
    echo -e "${BLUE}📥 Cloning repository from $REPO_URL...${NC}"
    git clone "$REPO_URL"
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to clone repository.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ Directory $DIR_NAME already exists, skipping clone.${NC}"
fi

cd "$DIR_NAME" || { echo -e "${RED}❌ Cannot enter directory $DIR_NAME.${NC}"; exit 1; }

# ---------------------- Python Version Check ----------------------
echo -e "${BLUE}🔍 Checking for compatible Python versions (>=3.7)...${NC}"
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
    echo -e "${RED}❌ No compatible Python (>=3.7) found. Please install Python 3.7 or higher.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found Python: $PYTHON_BIN${NC}"

# ---------------------- pip Check & Install ----------------------
echo -e "${BLUE}📦 Checking pip...${NC}"
if ! ($PYTHON_BIN -m pip --version &> /dev/null); then
    echo -e "${YELLOW}⚠️ pip not found, installing pip...${NC}"
    $PYTHON_BIN -m ensurepip --upgrade
fi

# ---------------------- Requirements Installation ----------------------
echo -e "${BLUE}📦 Installing dependencies from requirements.txt...${NC}"
$PYTHON_BIN -m pip install -r requirements.txt

# ---------------------- Database Setup ----------------------
echo -e "${BLUE}🗂️  Creating database directory...${NC}"
mkdir -p database

# ---------------------- Generate config.json ----------------------
if [ ! -f config.json ]; then
    echo -e "${BLUE}⚙️  Generating config.json template...${NC}"
    cat > config.json <<EOF
{
  "DISCORD_TOKEN": "",
  "OPENAI_API_KEY": "",
  "GUILD_ID": "",
  "OWNER_IDS": [],
  "DATABASE_PATH": "./database/data.db"
}
EOF
else
    echo -e "${YELLOW}⚠️ config.json already exists, skipping creation.${NC}"
fi

# ---------------------- Finished ----------------------
echo -e "${GREEN}🎉 Milo Bot installed successfully!${NC}"
echo -e "${YELLOW}📝 Please edit the config.json file to fill in your credentials.${NC}"
echo -e "${BLUE}📌 To start the bot, run:${NC}"
echo -e "   ${GREEN}$PYTHON_BIN main.py${NC}"
echo -e "${BLUE}📅 For update log, visit:${NC} https://github.com/msgaxzzz/Milo-discord-fun-bot/blob/main/CHANGELOG.md"
