import os
import re
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

logging.basicConfig(level=logging.INFO)

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

SOURCE_CHANNELS_STR = os.environ.get("SOURCE_CHANNELS", "")
SOURCE_CHANNELS = [int(ch.strip()) for ch in SOURCE_CHANNELS_STR.split(",") if ch.strip()]

TARGET_CHANNEL = int(os.environ.get("TARGET_CHANNEL", 0))

app = Client(
    "zk_dubbing_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    session_string=SESSION_STRING if SESSION_STRING else None
)

SAVED_BANNER_ID = None
current_tracking_episode = None

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

# 3. Banner save karne ki command: /setbanner (Sticker/Photo/Document par reply karein)
@app.on_message(filters.command("setbanner") & filters.private)
async def set_banner(client: Client, message: Message):
    global SAVED_BANNER_ID
    if message.reply_to_message and (message.reply_to_message.sticker or message.reply_to_message.photo or message.reply_to_message.document):
        reply_msg = message.reply_to_message
        if reply_msg.sticker:
            SAVED_BANNER_ID = reply_msg.sticker.file_id
        elif reply_msg.photo:
            SAVED_BANNER_ID = reply_msg.photo.file_id
        elif reply_msg.document:
            SAVED_BANNER_ID = reply_msg.document.file_id
            
        await message.reply("✅ Black line banner sticker successfully save ho gaya hai!")
    else:
        await message.reply("❌ Kripya kisi sticker ya photo par reply karke `/setbanner` command dein.")

# Helper function banner bhejne ke liye
async def send_banner_sticker(client, season, ep_num):
    global SAVED_BANNER_ID
    try:
        if SAVED_BANNER_ID:
            try:
                await client.send_cached_media(chat_id=TARGET_CHANNEL, file_id=SAVED_BANNER_ID)
            except:
                await client.send_message(chat_id=TARGET_CHANNEL, text=f"<b>⬇️  SEASON {season} • EPISODE {ep_num}  ⬇️</b>")
        else:
            await client.send_message(chat_id=TARGET_CHANNEL, text=f"<b>⬇️  SEASON {season} • EPISODE {ep_num}  ⬇️</b>")
    except Exception as e:
        print(f"Error sending banner: {e}")

# 4. Live Messages Handler (Sirf Photos, Videos aur Documents allow hain)
@app.on_message(filters.chat(SOURCE_CHANNELS) & (filters.photo | filters.video | filters.document))
async def auto_forward_anime(client: Client, message: Message):
    global current_tracking_episode
    try:
        orig_caption = message.caption or ""
        
        if message.photo:
            custom_caption, anime_name, _ = format_poster_caption(orig_caption)
            await message.copy(chat_id=TARGET_CHANNEL, caption=custom_caption)
            print(f"Poster Forwarded: {anime_name}")
            
        elif message.video or message.document:
            custom_caption, anime_name, ep_num, season = format_episode_caption(orig_caption)
            
            # Agar naya episode number aata hai, toh purane episode ke baad banner bhejo
            if current_tracking_episode and current_tracking_episode != ep_num:
                await send_banner_sticker(client, season, current_tracking_episode)
                await asyncio.sleep(1)
            
            current_tracking_episode = ep_num
            
            # Video file copy karein
            await message.copy(chat_id=TARGET_CHANNEL, caption=custom_caption)
            print(f"Episode Forwarded: {anime_name} - S{season} Ep {ep_num}")
            
    except Exception as e:
        print(f"Error in live message: {e}")

# 5. Command se purane episodes fetch karne ke liye: /fetch <channel_id> <limit>
@app.on_message(filters.command("fetch") & filters.private)
async def fetch_old_episodes(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        await message.reply("❌ Sahi format use karein:\n`/fetch <Channel_ID> <Limit>`")
        return
    
    try:
        chat_id = int(args[1])
        limit = int(args[2]) if len(args) > 2 else 50
        
        await message.reply(f"⏳ Channel `{chat_id}` se data scan ho raha hai...")
        
        count = 0
        last_ep = None
        async for msg in client.get_chat_history(chat_id, limit=limit):
            if msg.photo or msg.video or msg.document:
                orig_caption = msg.caption or ""
                
                if msg.photo:
                    custom_caption, _, _ = format_poster_caption(orig_caption)
                    await msg.copy(chat_id=TARGET_CHANNEL, caption=custom_caption)
                elif msg.video or msg.document:
                    custom_caption, _, ep_num, season = format_episode_caption(orig_caption)
                    
                    if last_ep and last_ep != ep_num:
                        await send_banner_sticker(client, season, last_ep)
                        await asyncio.sleep(1)
                    
                    last_ep = ep_num
                    await msg.copy(chat_id=TARGET_CHANNEL, caption=custom_caption)
                
                count += 1
                await asyncio.sleep(3)
                
        await message.reply(f"✅ Kaam poora ho gaya! Total `{count}` items bhej diye gaye hain.")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")

if __name__ == "__main__":
    print("ZK Dubbing Studio Ultimate Bot started successfully...")
    app.run()
