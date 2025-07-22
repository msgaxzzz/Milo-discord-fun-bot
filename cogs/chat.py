import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import json
from collections import defaultdict
import asyncio

class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.conversations = defaultdict(list)
        self.load_config()
        self.bot.loop.create_task(self.setup_database())

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.default_api_key = config.get("OPENAI_API_KEY")
                self.api_base = config.get("OPENAI_API_BASE", "https://api.openai.com/v1")
                self.allow_user_keys = config.get("ALLOW_USER_KEYS", True)
                self.default_model = config.get("DEFAULT_CHAT_MODEL", "gpt-3.5-turbo")
                self.allowed_models = config.get("ALLOWED_CHAT_MODELS", ["gpt-3.5-turbo"])
                self.google_api_key = config.get("GOOGLE_API_KEY")
                self.google_cse_id = config.get("GOOGLE_CSE_ID")
        except (FileNotFoundError, json.JSONDecodeError):
            self.default_api_key, self.api_base, self.default_model = None, "https://api.openai.com/v1", "gpt-3.5-turbo"
            self.allow_user_keys, self.allowed_models = True, ["gpt-3.5-turbo"]
            self.google_api_key, self.google_cse_id = None, None
        
        self.enable_web_search = bool(self.google_api_key and self.google_cse_id)

    async def setup_database(self):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS guild_configs (
                    guild_id INTEGER PRIMARY KEY,
                    openai_key TEXT,
                    persona TEXT
                )
            ''')
            try:
                await cursor.execute("ALTER TABLE guild_configs ADD COLUMN persona TEXT")
            except Exception: pass
        await self.bot.db.commit()

    async def get_guild_config(self, guild_id: int):
        if not guild_id: return None, None
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT openai_key, persona FROM guild_configs WHERE guild_id = ?", (guild_id,))
            return await cursor.fetchone()

    async def set_guild_key(self, guild_id: int, key: str = None):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT OR IGNORE INTO guild_configs (guild_id) VALUES (?)", (guild_id,))
            await cursor.execute("UPDATE guild_configs SET openai_key = ? WHERE guild_id = ?", (key, guild_id))
        await self.bot.db.commit()

    async def set_guild_persona(self, guild_id: int, persona: str = None):
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("INSERT OR IGNORE INTO guild_configs (guild_id) VALUES (?)", (guild_id,))
            await cursor.execute("UPDATE guild_configs SET persona = ? WHERE guild_id = ?", (persona, guild_id))
        await self.bot.db.commit()
    
    chat_config = app_commands.Group(name="chat-config", description="Configure the AI chat settings for a server.", guild_only=True)

    @chat_config.command(name="set-key", description="Set a custom OpenAI API key for this server.")
    @app_commands.describe(key="Your OpenAI API key. Use 'reset' to remove.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_key(self, interaction: discord.Interaction, key: str):
        if not self.allow_user_keys:
            await interaction.response.send_message("The bot owner has disabled custom API keys.", ephemeral=True)
            return
        if key.lower() == 'reset':
            await self.set_guild_key(interaction.guild.id)
            await interaction.response.send_message("✅ Server API key removed.", ephemeral=True)
            return
        await self.set_guild_key(interaction.guild.id, key)
        await interaction.response.send_message("✅ Server API key saved.", ephemeral=True)

    @chat_config.command(name="set-persona", description="Set a custom personality for the AI.")
    @app_commands.describe(persona="A description of the AI's personality. Use 'reset' to remove.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_persona(self, interaction: discord.Interaction, persona: str):
        if len(persona) > 500:
            await interaction.response.send_message("Persona is too long (max 500 chars).", ephemeral=True)
            return
        if persona.lower() == 'reset':
            await self.set_guild_persona(interaction.guild.id)
            await interaction.response.send_message("✅ AI persona reset to default.", ephemeral=True)
            return
        await self.set_guild_persona(interaction.guild.id, persona)
        await interaction.response.send_message("✅ AI persona updated.", ephemeral=True)

    @chat_config.command(name="view", description="View the current chat configuration.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_config(self, interaction: discord.Interaction):
        guild_config = await self.get_guild_config(interaction.guild.id) or (None, None)
        guild_key, guild_persona = guild_config
        embed = discord.Embed(title=f"Chat Configuration for {interaction.guild.name}", color=discord.Color.blue())
        key_status = "⚠️ Not Configured"
        if guild_key: key_status = f"`{guild_key[:5]}...{guild_key[-4:]}` (Custom)"
        elif self.default_api_key: key_status = "Using Bot's Default Key"
        embed.add_field(name="Server API Key", value=key_status, inline=False)
        embed.add_field(name="AI Persona", value=guild_persona or "Default (Friendly, helpful, and web-enabled)", inline=False)
        embed.add_field(name="Web Search", value="✅ Enabled" if self.enable_web_search else "⚠️ Disabled (Bot owner has not configured Google API keys)", inline=False)
        embed.add_field(name="API Base URL", value=f"`{self.api_base}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def define_tools(self):
        return [{"type": "function", "function": { "name": "google_search", "description": "Get real-time information from the web for recent events or specific data.", "parameters": { "type": "object", "properties": {"query": {"type": "string", "description": "The search query."}}, "required": ["query"]}}}]

    async def execute_google_search(self, query: str):
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.google_api_key,
            'cx': self.google_cse_id,
            'q': query,
            'num': 5 # Request top 5 results
        }
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("items", [])
                    snippets = [item.get("snippet", "") for item in items]
                    return json.dumps({"results": snippets}) if snippets else json.dumps({"error": "No results found."})
                else:
                    error_data = await response.json()
                    error_message = error_data.get("error", {}).get("message", "Unknown error.")
                    return json.dumps({"error": f"Failed to fetch search results. Status: {response.status} - {error_message}"})
        except Exception as e:
            return json.dumps({"error": f"An error occurred during search: {str(e)}"})

    async def model_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=model, value=model) for model in self.allowed_models if current.lower() in model.lower()]

    @app_commands.command(name="chat", description="Chat with the AI, with optional live web search.")
    @app_commands.describe(prompt="What to talk about?", model="Choose a specific AI model.", search_web="Set to 'True' to allow the AI to search the web for current info.")
    @app_commands.autocomplete(model=model_autocomplete)
    @app_commands.checks.cooldown(1, 8, key=lambda i: i.user.id)
    async def chat(self, interaction: discord.Interaction, prompt: str, model: str = None, search_web: bool = False):
        await interaction.response.defer()
        
        # --- 新增：优雅处理未配置的情况 ---
        if search_web and not self.enable_web_search:
            await interaction.followup.send("Sorry, the web search feature is not configured by the bot owner. I cannot perform a web search.", ephemeral=True)
            return
            
        context_id = interaction.channel.id if interaction.guild else interaction.user.id
        chosen_model = model or self.default_model

        guild_config = await self.get_guild_config(interaction.guild.id) or (None, None)
        api_key, persona = guild_config

        if not api_key: api_key = self.default_api_key
        if not api_key:
            await interaction.followup.send("AI chat is not configured. An admin must set an API key.", ephemeral=True)
            return

        if context_id not in self.conversations:
            system_prompt_content = persona or ("You are Milo, a friendly and helpful Discord bot. You can access real-time information using the 'google_search' tool for current events or specific data. Keep your answers concise and engaging.")
            self.conversations[context_id].append({"role": "system", "content": system_prompt_content})
        
        self.conversations[context_id].append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        payload = {"model": chosen_model, "messages": self.conversations[context_id]}
        if self.enable_web_search and search_web:
            payload["tools"] = self.define_tools()
            payload["tool_choice"] = "auto"
        
        try:
            async with self.session.post(f"{self.api_base}/chat/completions", headers=headers, json=payload) as response:
                if not response.status == 200:
                    error_data = await response.json()
                    error_message = error_data.get('error', {}).get('message', 'An unknown API error occurred.')
                    self.conversations[context_id].pop()
                    await interaction.followup.send(f"**API Error:** {response.status} - {error_message}", ephemeral=True)
                    return

                data = await response.json()
                ai_message = data['choices'][0]['message']
                
                if ai_message.get("tool_calls") and self.enable_web_search and search_web:
                    thinking_message = await interaction.followup.send("🔎 *Searching the web...*", wait=True)
                    
                    self.conversations[context_id].append(ai_message)
                    tool_call = ai_message["tool_calls"][0]
                    function_name = tool_call['function']['name']
                    function_args = json.loads(tool_call['function']['arguments'])
                    query = function_args.get("query")
                    
                    tool_response = await self.execute_google_search(query)
                    
                    self.conversations[context_id].append({"tool_call_id": tool_call['id'], "role": "tool", "name": function_name, "content": tool_response})
                    
                    final_payload = {"model": chosen_model, "messages": self.conversations[context_id]}
                    async with self.session.post(f"{self.api_base}/chat/completions", headers=headers, json=final_payload) as final_response:
                        final_data = await final_response.json()
                        final_answer = final_data['choices'][0]['message']['content']
                        await thinking_message.edit(content=final_answer)
                else:
                    final_answer = ai_message['content']
                    await interaction.edit_original_response(content=final_answer)

                self.conversations[context_id].append({"role": "assistant", "content": final_answer})
                if len(self.conversations[context_id]) > 10:
                    self.conversations[context_id] = self.conversations[context_id][0:1] + self.conversations[context_id][-9:]

        except Exception as e:
            print(f"Chat processing error: {e}")
            await interaction.followup.send("An unexpected error occurred. Please check the console.", ephemeral=True)

    @app_commands.command(name="chat-reset", description="Resets your conversation history with the AI.")
    async def chat_reset(self, interaction: discord.Interaction):
        context_id = interaction.channel.id if interaction.guild else interaction.user.id
        if context_id in self.conversations:
            self.conversations.pop(context_id)
        await interaction.response.send_message("🤖 Your conversation history has been reset.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Chat(bot))