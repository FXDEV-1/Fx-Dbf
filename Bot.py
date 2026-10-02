import discord
from discord import app_commands
from discord.ext import commands
import os
import re
import base64
import tempfile
import aiohttp

# Token comes from environment variable (never hardcode it)
TOKEN = os.getenv("MTU1MzMzNDM5MTE5ODE5NTg0Mw.GVnjp3.B0HrZXaqxk_ECByEnGInYbozV1tn459GR2jPiA")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def simple_normalize(code: str) -> str:
    """Basic safe partial normalization (not full commercial deobfuscation)."""
    # Try to decode obvious base64 strings
    def try_b64(m):
        try:
            decoded = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
            if decoded.isprintable() and len(decoded) > 3:
                return f'"{decoded}"'
        except Exception:
            pass
        return m.group(0)

    code = re.sub(r'["\']([A-Za-z0-9+/=]{16,})["\']', try_b64, code)

    # Expand simple string.char(num, num, ...)
    def expand_char(m):
        try:
            nums = [int(x.strip()) for x in m.group(1).split(",")]
            chars = "".join(chr(n) for n in nums if 0 <= n < 256)
            return f'"{chars}"'
        except Exception:
            return m.group(0)

    code = re.sub(r'string\.char\(([^)]+)\)', expand_char, code)

    # Basic \xHH escape decoding
    code = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), code)

    return code

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print("Sync error:", e)

@bot.tree.command(name="deobf", description="Partially normalize obfuscated Lua/Luau code")
@app_commands.describe(
    file="Upload a .lua / .luau / .txt file",
    url="Public URL to the script",
    code="Paste short code directly"
)
async def deobf(
    interaction: discord.Interaction,
    file: discord.Attachment = None,
    url: str = None,
    code: str = None
):
    await interaction.response.defer(thinking=True)

    source = None
    filename = "input.lua"

    try:
        if file:
            if file.size > 2_000_000:
                await interaction.followup.send("File too large (max \~2 MB).")
                return
            raw = await file.read()
            source = raw.decode("utf-8", errors="replace")
            filename = file.filename or filename
        elif url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(f"Could not fetch URL (status {resp.status}).")
                        return
                    source = await resp.text()
        elif code:
            source = code
        else:
            await interaction.followup.send("Please provide a file, a URL, or paste some code.")
            return

        if not source or not source.strip():
            await interaction.followup.send("Empty input.")
            return

        result = simple_normalize(source)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_partial.lua", delete=False, encoding="utf-8"
        ) as f:
            f.write(result)
            temp_path = f.name

        await interaction.followup.send(
            content=(
                "**Partial normalization only**\n"
                "This is a basic cleaner / learning bot — it does **not** fully deobfuscate "
                "commercial protectors (MoonSec, Luraph, IronBrew, etc.)."
            ),
            file=discord.File(temp_path, filename=filename.replace(".lua", "_partial.lua").replace(".luau", "_partial.luau"))
        )
        os.unlink(temp_path)

    except Exception as e:
        await interaction.followup.send(f"Error: `{type(e).__name__}: {e}`")

if __name__ == "__main__":
    bot.run(MTU1MzMzNDM5MTE5ODE5NTg0Mw.GVnjp3.B0HrZXaqxk_ECByEnGInYbozV1tn459GR2jPiA)
