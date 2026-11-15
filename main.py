import os
import re
import logging
import asyncio
from aiohttp import web

# Python 3.14 event loop fix for global client initialization
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from hydrogram import Client, filters
from hydrogram.types import Message

logging.basicConfig(level=logging.INFO)

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

app = Client(
    "zk_dubbing_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    session_string=SESSION_STRING if SESSION_STRING else None
)

SOURCE_TO_TARGET = {}
TARGET_BANNERS = {}
CURRENT_TRACKING_EPISODES = {}

# --- Fake Web Server for Render Free Web Service Port Binding ---
async def handle_ping(request):
    return web.Response(text="ZK Dubbing Bot is active and running!")

async def start_web_server():
    web_app = web.Application()
    web_app.add_routes([web.get('/', handle_ping)])
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# 1. Poster Caption Auto-Parser
def format_poster_caption(orig_caption):
    lines = [line.strip() for line in orig_caption.split('\n') if line.strip()]
    anime_name = lines[0] if lines else "Anime Series"
    
    season_match = re.search(r'season\s*[:\-]?\s*(\d+|tba)', orig_caption, re.IGNORECASE)
    season = season_match.group(1).upper() if season_match else "01"
    
    genre_match = re.search(r'genres?\s*[:\-]?\s*(.+)', orig_caption, re.IGNORECASE)
    genres = genre_match.group(1).strip() if genre_match else "Romance, Fantasy, Supernatural"
    
    if re.search(r'fandub', orig_caption, re.IGNORECASE):
        audio_type = "[Hindi] #FanDub"
    else:
        audio_type = "[Hindi] #Official"
        
    custom_caption = (
        f"🎬 ANIME : {anime_name}\n\n"
        f"❖ Season: {season}\n"
        f"❖ EPISODES: TBA\n"
        f"❖ AUDIO: {audio_type}\n"
        f"❖ QUALITY: 480p • 720p • 1080p\n"
        f"❖ GENRES: {genres}\n\n"
        f"Join Our Channel's @zyphorkagex"
    )
    return custom_caption, anime_name, season

# 2. Episode Caption Auto-Parser
def format_episode_caption(orig_caption):
    ep_match = re.search(r'(?:ep|episode|e)\s*[-:]?\s*(\d+)', orig_caption, re.IGNORECASE)
    ep_num = ep_match.group(1) if ep_match else "1"
    
    season_match = re.search(r'season\s*[:\-]?\s*(\d+)', orig_caption, re.IGNORECASE)
    season = season_match.group(1) if season_match else "1"
    
    qual_match = re.search(r'(360p|480p|720p|1080p|4k)', orig_caption, re.IGNORECASE)
    quality = qual_match.group(1) if qual_match else "720p"
    
    if re.search(r'fandub', orig_caption, re.IGNORECASE):
        audio_tag = "#FanDub"
    else:
        audio_tag = "#Official"
        
    lines = [line.strip() for line in orig_caption.split('\n') if line.strip()]
    anime_name = lines[0] if lines else "Anime Series"
    
    custom_caption = (
        f"**{anime_name}**\n\n"
        f"‣ Episodes: **{ep_num}**\n"
        f"‣ Audio track: Hindi | {audio_tag}\n"
        f"‣ Quality: **{quality}**\n\n"
        f"⌬ Pᴏᴡᴇʀᴇᴅ Bʏ: [ @zyphorkagex ]"
    )
    return custom_caption, anime_name, ep_num, season

# --- MAPPING & CONFIG COMMANDS ---

@app.on_message(filters.command("link") & filters.private)
async def link_channels(client: Client, message: Message):
    global SOURCE_TO_TARGET
    args = message.command
    if len(args) < 3:
        await message.reply("❌ Sahi format use karein:\n`/link <Source_ID> <Target_ID>`")
        return
    try:
        src = int(args[1])
        tgt = int(args[2])
        SOURCE_TO_TARGET[src] = tgt
        await message.reply(f"✅ Successfully Linked!\n📂 Source: `{src}`\n🎯 Target: `{tgt}`")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")

@app.on_message(filters.command("unlink") & filters.private)
async def unlink_channel(client: Client, message: Message):
    global SOURCE_TO_TARGET
    args = message.command
    if len(args) < 2:
        await message.reply("❌ Sahi format:\n`/unlink <Source_ID>`")
        return
    try:
        src = int(args[1])
        if src in SOURCE_TO_TARGET:
            del SOURCE_TO_TARGET[src]
            await message.reply(f"✅ Source `{src}` ko unlink kar diya gaya hai.")
        else:
            await message.reply("⚠️ Yeh source ID list mein nahi mili.")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")

@app.on_message(filters.command("listlinks") & filters.private)
async def list_links(client: Client, message: Message):
    if not SOURCE_TO_TARGET:
        await message.reply("📂 Filhal koi bhi source-target link nahi kiya gaya hai.")
        return
    
    text = "📋 **Active Channel Links:**\n\n"
    for src, tgt in SOURCE_TO_TARGET.items():
        text += f"• Source: `{src}`\n  ➡️ Target: `{tgt}`\n\n"
    await message.reply(text)

@app.on_message(filters.command("setbanner") & filters.private)
async def set_banner(client: Client, message: Message):
    global TARGET_BANNERS
    args = message.command
    if len(args) < 2:
        await message.reply("❌ Sahi format:\n`/setbanner <Target_Channel_ID>` (Media par reply karein)")
        return
    
    try:
        tgt = int(args[1])
        if message.reply_to_message and (message.reply_to_message.sticker or message.reply_to_message.photo or message.reply_to_message.document):
            reply_msg = message.reply_to_message
            if reply_msg.sticker:
                b_id = reply_msg.sticker.file_id
            elif reply_msg.photo:
                b_id = reply_msg.photo.file_id
            elif reply_msg.document:
                b_id = reply_msg.document.file_id
            else:
                return
            
            TARGET_BANNERS[tgt] = b_id
            await message.reply(f"✅ Target `{tgt}` ke liye banner sticker successfully save ho gaya hai!")
        else:
            await message.reply("❌ Kripya media par reply karein.")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")

async def send_banner_sticker(client, target_channel, season, ep_num):
    try:
        banner_id = TARGET_BANNERS.get(target_channel)
        if banner_id:
            try:
                await client.send_cached_media(chat_id=target_channel, file_id=banner_id)
            except:
                await client.send_message(target_channel, text=f"<b>⬇️  SEASON {season} • EPISODE {ep_num}  ⬇️</b>")
        else:
            await client.send_message(target_channel, text=f"<b>⬇️  SEASON {season} • EPISODE {ep_num}  ⬇️</b>")
    except Exception as e:
        print(f"Error sending banner: {e}")

@app.on_message(filters.chat(lambda _, msg: msg.chat.id in SOURCE_TO_TARGET) & (filters.photo | filters.video | filters.document))
async def auto_forward_anime(client: Client, message: Message):
    global CURRENT_TRACKING_EPISODES
    try:
        src_chat = message.chat.id
        target_channel = SOURCE_TO_TARGET.get(src_chat)
        if not target_channel:
            return
            
        orig_caption = message.caption or ""
        
        if message.photo:
            custom_caption, anime_name, _ = format_poster_caption(orig_caption)
            await message.copy(chat_id=target_channel, caption=custom_caption)
            print(f"Poster Forwarded to {target_channel} from {src_chat}")
            
        elif message.video or message.document:
            custom_caption, anime_name, ep_num, season = format_episode_caption(orig_caption)
            
            track_key = f"{src_chat}_{target_channel}"
            last_ep = CURRENT_TRACKING_EPISODES.get(track_key)
            
            if last_ep and last_ep != ep_num:
                await send_banner_sticker(client, target_channel, season, last_ep)
                await asyncio.sleep(1)
            
            CURRENT_TRACKING_EPISODES[track_key] = ep_num
            
            await message.copy(chat_id=target_channel, caption=custom_caption)
            print(f"Episode Forwarded to {target_channel}: S{season} Ep {ep_num}")
            
    except Exception as e:
        print(f"Error in live message: {e}")

@app.on_message(filters.command("fetch") & filters.private)
async def fetch_old_episodes(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        await message.reply("❌ Sahi format use karein:\n`/fetch <Source_Channel_ID> <Limit>`")
        return
    
    try:
        src_chat = int(args[1])
        target_channel = SOURCE_TO_TARGET.get(src_chat)
        if not target_channel:
            await message.reply("❌ Pehle is source channel ko target ke sath link karein:\n`/link <Source_ID> <Target_ID>`")
            return
            
        limit = int(args[2]) if len(args) > 2 else 50
        
        await message.reply(f"⏳ Source `{src_chat}` se data scan ho kar Target `{target_channel}` par bhej raha hai...")
        
        count = 0
        last_ep = None
        async for msg in client.get_chat_history(src_chat, limit=limit):
            if msg.photo or msg.video or msg.document:
                orig_caption = msg.caption or ""
                
                if msg.photo:
                    custom_caption, _, _ = format_poster_caption(orig_caption)
                    await message.copy(chat_id=target_channel, caption=custom_caption)
                elif msg.video or msg.document:
                    custom_caption, _, ep_num, season = format_episode_caption(orig_caption)
                    
                    if last_ep and last_ep != ep_num:
                        await send_banner_sticker(client, target_channel, season, last_ep)
                        await asyncio.sleep(1)
                    
                    last_ep = ep_num
                    await message.copy(chat_id=target_channel, caption=custom_caption)
                
                count += 1
                await asyncio.sleep(3)
                
        await message.reply(f"✅ Kaam poora ho gaya! Total `{count}` items target channel par bhej diye gaye hain.")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")

async def main():
    await start_web_server()
    async with app:
        print("ZK Multi-Studio Dubbing Bot started successfully...")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
