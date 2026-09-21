import discord
from discord.ext import commands, tasks
import random
import asyncio
import json
import os
import glob
import uuid
from datetime import datetime, timedelta, time, timezone
import pytz
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# =====================================================================
# CONFIG
# =====================================================================
SCAM_CHANNEL_ID = 1403567670229729423
IMMUNE_ROLE_ID = 1386995499306848310
BONUS_ROLE_ID = 1237698075989114942
LOG_CHANNEL_ID = 1449020423663783936
CHANNEL_ID = 1233440140748128288
WELCOME_CHANNEL_ID = 1233453277207859232
DEFAULT_ROLE_ID = 1237644257934704713

ROLE_LEVELS = [
    1403605505590689885,
    1403605764831969371,
    1403605883262341240,
    1403606299735756840,
    1403605754056806450,
    1403606581937049740,
    1403606476077011035,
]
LEVEL_EXP = [100, 3000, 11000, 18000, 28000, 38000, 50000]
EXP_COOLDOWN = 15
EXP_MIN = 3
EXP_MAX = 9
ROULETTE_COOLDOWN_SECONDS = 3

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
VN_OFFSET = timezone(timedelta(hours=7))
TARGET_DATE = datetime(2026, 6, 10)

ROULETTE_FILE = "umiroulette_data.json"
EXP_FILE = "exp_data.json"
ROLES_BACKUP_FILE = "roles_backup.json"

EMOJI_LIST = [
    "<:AoLewd:1398351742789226636>", "<:doropium:1398351738108641290>",
    "<:ShikiSmug:1398351730181411088>", "<:UmiSip:1398351745779892325>",
    "<:UmiEmbarrassed:1398351749361832089>", "<:nice:1391968396387549224>",
    "<:wut:1391968406143504466>", "<:dorothy:1393268584536342548>",
    "<:HarukaSalute:1398351733767278742>", "<a:nod:1404327366490329169>",
]

# Simple text -> local file responses
FILE_RESPONSES = {
    "simp": "simp.jpg",
    "khó": "khó.png",
    "vl": "vl.png",
    "sybau": "sybau.jpg",
    "chọn đi": "chon.png",
    "hi chat": "hi.gif",
    "thoát khỏi lớp da thịt": "thit.png",
    "fembi": "fembi.png",
    "femboi": "femboi.png",
    "chill": "cortisol.jpg",
}

# Simple text -> gif/link responses
GIF_RESPONSES = {
    "pat pat": "https://tenor.com/view/shiro-anime-no-game-no-life-headpat-cute-gif-17317343567086759130",
    "pat": "https://tenor.com/view/anime-pat-anime-gif-26506449",
    "hmph": "https://tenor.com/view/nananiji-hm-hmm-hmph-eh-gif-4830821874963593839",
    "nekogn": "https://tenor.com/view/osaka-azuman-goodnight-gn-sleep-gif-24066064",
    "nekogm": "https://tenor.com/view/little-witch-academia-good-morning-gif-24763182",
    "owo": "https://tenor.com/view/kanna-kamui-kobayashis-dragon-maid-anime-sparkling-eyes-gif-16297310",
    "yuri": "https://giphy.com/embed/OGXilB8foNFIs",
    "bye bye": "https://tenor.com/view/anime-bye-bye-maki-wave-soredemo-ayumu-wa-yosetekuru-when-will-ayumu-make-his-move-gif-26195508",
    "time": "https://tenor.com/view/tik-tok-meme-waiting-wait-time-gif-16450082290173148616",
    "study": "https://tenor.com/view/dragon-maid-kanna-eraser-anime-homework-gif-886305399648227690",
    "angry": "https://tenor.com/view/angry-thiago-mad-angry-fist-emoji-gif-17761307",
    "exam": "https://tenor.com/view/madara-uchiha-padai-learning-anime-uchiha-gif-10063372275053411217",
    "please": "https://tenor.com/view/please7tv-please-beg-pray-hope-gif-3860103425950934673",
}

# Text -> glob pattern for random image pick
NEKOQT_PATTERNS = {
    "nekoqt nishiya": "nishiya*.jpg",
    "nekoqt bin": "bin*.jpg",
    "nekoqt nguyên": "nguyên*.jpg",
    "nekoqt vinh": "vinh*.png",
    "nekoqt cáo": "fox*.jpg",
}

REACTION_KEYWORDS = ["nishi", "admin", "nishiya"]

WEEKLY_SCHEDULE_ROLE_IDS = {
    "vip_immune_id": 842942662977781761,
}
PROTECTED_MUTE_IDS = {
    "842942662977781761", "1284520590954463302",
    "1198110578988818513", "1235666148964434022",
}


# =====================================================================
# BOT SETUP
# =====================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class NekoBot(commands.Bot):
    async def setup_hook(self):
        # setup_hook runs exactly once per process, before the client
        # connects, so it's the right place for one-time startup tasks
        # (starting task loops, scheduling background sends, syncing
        # the command tree). Doing this in on_ready instead would
        # duplicate everything on every reconnect.
        await self.tree.sync()
        daily_countdown_task.start()

        self.loop.create_task(schedule_message(
            self, CHANNEL_ID, time(0, 0),
            "https://tenor.com/view/osaka-azuman-goodnight-gn-sleep-gif-24066064"))
        self.loop.create_task(schedule_message(
            self, CHANNEL_ID, time(3, 0),
            "https://tenor.com/view/blend-s-bathroom-banio-trap-anime-gif-10374444"))
        self.loop.create_task(schedule_message(
            self, CHANNEL_ID, time(6, 0),
            "https://tenor.com/view/little-witch-academia-good-morning-gif-24763182"))
        self.loop.create_task(schedule_message_weekly(
            self, CHANNEL_ID, 0, time(7, 0),
            "https://tenor.com/view/monday-konata-alkruhn-monday-moment-gif-25525919"))
        self.loop.create_task(schedule_message_weekly(
            self, CHANNEL_ID, 6, time(21, 0), "Sunday.png"))


bot = NekoBot(command_prefix="^", intents=intents)
tree = bot.tree

active_giveaways = {}
last_exp_time = {}
user_cooldowns = {}


def bot_avatar_url():
    """Safe avatar URL getter — falls back to default avatar if unset."""
    if bot.user.avatar:
        return bot.user.avatar.url
    return bot.user.default_avatar.url


def author_avatar_url(member):
    return member.avatar.url if member.avatar else member.default_avatar.url


# =====================================================================
# LOGGING HELPERS
# =====================================================================
def log_message_to_file(message: discord.Message, log_path="messages.log"):
    with open(log_path, "a", encoding="utf8") as log_file:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        guild_name = message.guild.name if message.guild else "DM"
        log_file.write(
            f"[{time_str}] {guild_name} #{message.channel} | "
            f"{message.author.name}: {message.content}\n"
        )


async def log_to_channel(message: discord.Message, action: str):
    if message.author.bot or not message.guild:
        return

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        print(f"[LOG ERROR] Cannot find log channel with ID: {LOG_CHANNEL_ID}")
        return

    color = {
        "NEW": discord.Color.blue(),
        "DELETED": discord.Color.red(),
    }.get(action, discord.Color.yellow())

    embed = discord.Embed(
        title=f"[{action}] Tin nhắn {message.author.display_name}",
        description=message.content if message.content else "*Không có nội dung văn bản*",
        color=color,
    )
    embed.set_author(
        name=f"{message.author.display_name} ({message.author.id})",
        icon_url=author_avatar_url(message.author),
    )
    embed.add_field(name="Kênh Gốc", value=message.channel.mention, inline=False)
    embed.set_footer(text=f"ID tin nhắn: {message.id}")

    attachment_files = []
    attachment_urls = []
    for attachment in message.attachments:
        if attachment.size < 8 * 1024 * 1024:
            try:
                attachment_files.append(await attachment.to_file())
            except Exception:
                attachment_urls.append(attachment.url)
        else:
            attachment_urls.append(attachment.url)

    await log_channel.send(embed=embed, files=attachment_files if attachment_files else None)

    if attachment_urls:
        url_list = "\n".join(attachment_urls)
        await log_channel.send(f"**[Attachments/Large Files from {message.channel.mention}]**\n{url_list}")


# =====================================================================
# SCHEDULED MESSAGES
# =====================================================================
async def _send_scheduled_content(channel, content: str):
    """Shared send logic for both the daily and weekly schedulers."""
    content_lower = content.lower()
    if content_lower.endswith(('.png', '.jpg', '.gif')):
        try:
            await channel.send(file=discord.File(content))
        except FileNotFoundError:
            await channel.send(f"❌ Lỗi: Không tìm thấy file `{content}` trong thư mục.")
        except Exception as e:
            await channel.send(f"❌ Lỗi gửi file: {e}")
    elif content.strip():
        await channel.send(content)


async def schedule_message_weekly(bot_instance, channel_id, target_day_of_week: int,
                                   send_time: time, message_content: str):
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        now = datetime.now(VN_TZ)
        days_until_target = (target_day_of_week - now.weekday() + 7) % 7
        target_time = now.replace(hour=send_time.hour, minute=send_time.minute,
                                   second=0, microsecond=0)
        next_send_time = (now + timedelta(days=days_until_target)).replace(
            hour=send_time.hour, minute=send_time.minute, second=0, microsecond=0
        )
        if days_until_target == 0 and now > target_time:
            next_send_time += timedelta(days=7)

        wait_seconds = (next_send_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        channel = bot_instance.get_channel(channel_id)
        if channel:
            await _send_scheduled_content(channel, message_content)

        await asyncio.sleep(1)


async def schedule_message(bot_instance, channel_id, send_time: time, message_content: str):
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        now = datetime.now(VN_TZ)
        target = now.replace(hour=send_time.hour, minute=send_time.minute,
                              second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        channel = bot_instance.get_channel(channel_id)
        if channel:
            await _send_scheduled_content(channel, message_content)

        await asyncio.sleep(1)


# =====================================================================
# COUNTDOWN CARD
# =====================================================================
def get_font(size):
    font_paths = [
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def get_countdown_diff():
    """Shared diff calculation used by both the daily task and nekotime."""
    now = datetime.now(VN_OFFSET).replace(tzinfo=None)
    return TARGET_DATE - now


def create_countdown_card(days, hours, minutes):
    width, height = 500, 150
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle([10, 10, 490, 140], radius=60, fill=(35, 39, 50))

    font_text = get_font(22)
    font_number = get_font(24)
    font_unit = get_font(14)

    text = "DAYS REMAINING"
    text_bbox = draw.textbbox((0, 0), text, font=font_text)
    text_w = text_bbox[2] - text_bbox[0]
    draw.text(((width - text_w) // 2, 22), text, fill=(114, 154, 240), font=font_text)

    labels = [(str(days), "Days"), (str(hours), "Hours"), (str(minutes), "Minutes")]
    box_width = 110
    box_height = 40
    gap = 20
    total_width = len(labels) * box_width + (len(labels) - 1) * gap
    start_x = (width - total_width) // 2

    for val, unit in labels:
        val_bbox = draw.textbbox((0, 0), val, font=font_number)
        val_w = val_bbox[2] - val_bbox[0]
        unit_bbox = draw.textbbox((0, 0), unit, font=font_unit)
        unit_w = unit_bbox[2] - unit_bbox[0]

        box_center_x = start_x + box_width // 2
        box_y = 85

        draw.rounded_rectangle(
            [start_x, box_y, start_x + box_width, box_y + box_height],
            radius=20, fill=(255, 230, 235)
        )

        combined_w = val_w + 6 + unit_w
        text_start_x = box_center_x - combined_w // 2

        draw.text((text_start_x, box_y + 8), val, fill=(240, 128, 150), font=font_number)
        draw.text((text_start_x + val_w + 6, box_y + 13), unit, fill=(240, 128, 150), font=font_unit)

        start_x += box_width + gap

    # Use a unique filename so concurrent calls (auto task + manual
    # command firing close together) never read/write the same file.
    file_path = f"countdown_{uuid.uuid4().hex}.png"
    image.save(file_path)
    return file_path


@tasks.loop(time=time(10, 0, tzinfo=VN_OFFSET))
async def daily_countdown_task():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    diff = get_countdown_diff()
    if diff.total_seconds() > 0:
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        file_path = create_countdown_card(days, hours, minutes)
        try:
            await channel.send(file=discord.File(file_path))
        finally:
            os.remove(file_path)
    else:
        await channel.send("")


@daily_countdown_task.before_loop
async def before_daily_countdown():
    await bot.wait_until_ready()


# =====================================================================
# EXP / LEVEL SYSTEM
# =====================================================================
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


for _file in [ROULETTE_FILE, EXP_FILE, ROLES_BACKUP_FILE]:
    if not os.path.exists(_file):
        save_json(_file, {})


async def add_exp(member: discord.Member, amount: int):
    data = load_json(EXP_FILE)
    uid = str(member.id)

    if uid not in data:
        data[uid] = {"exp": 0, "level": 1}
    elif isinstance(data[uid], int):
        old_exp = data[uid]
        data[uid] = {"exp": old_exp, "level": 1}
        for i in range(len(LEVEL_EXP) - 1, -1, -1):
            if data[uid]["exp"] >= LEVEL_EXP[i]:
                data[uid]["level"] = i + 1
                break

    data[uid]["exp"] += amount

    for i in range(len(LEVEL_EXP) - 1, -1, -1):
        if data[uid]["exp"] >= LEVEL_EXP[i]:
            if data[uid]["level"] != i + 1:
                data[uid]["level"] = i + 1
                for rid in ROLE_LEVELS:
                    role = member.guild.get_role(rid)
                    if role in member.roles:
                        await member.remove_roles(role)

                new_role = member.guild.get_role(ROLE_LEVELS[i])
                if new_role:
                    await member.add_roles(new_role)
                    try:
                        await member.send(
                            f"<:smile:1541012583518048318> Chúc mừng! Bạn đã lên cấp **{i + 1}** và nhận role **{new_role.name}**!"
                        )
                    except discord.Forbidden:
                        pass
            break

    save_json(EXP_FILE, data)


def get_exp_info(user_id: str):
    data = load_json(EXP_FILE)
    uid = str(user_id)

    if uid not in data:
        return {"exp": 0, "level": 1, "progress": 0.0, "current_exp": 0,
                "next_exp": LEVEL_EXP[1], "is_max": False}

    user_data = data[uid]
    if isinstance(user_data, int):
        exp = user_data
        level = 1
        for i in range(len(LEVEL_EXP) - 1, -1, -1):
            if exp >= LEVEL_EXP[i]:
                level = i + 1
                break
    else:
        exp = user_data["exp"]
        level = user_data["level"]

    if level >= len(LEVEL_EXP):
        return {"exp": exp, "level": level, "progress": 100.0,
                "current_exp": exp, "next_exp": exp, "is_max": True}

    current_level_exp = LEVEL_EXP[level - 1]
    next_level_exp = LEVEL_EXP[level]
    exp_needed = next_level_exp - current_level_exp
    exp_gained = exp - current_level_exp
    progress = (exp_gained / exp_needed) * 100 if exp_needed > 0 else 100

    return {
        "exp": exp, "level": level, "progress": progress,
        "current_exp": exp_gained, "next_exp": exp_needed, "is_max": False,
    }


# =====================================================================
# EVENTS
# =====================================================================
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    """Khi member join - gắn role VÀ gửi welcome"""
    try:
        backup_data = load_json(ROLES_BACKUP_FILE)
        guild_id = str(member.guild.id)
        user_id = str(member.id)

        if guild_id in backup_data and user_id in backup_data[guild_id]:
            saved_role_ids = backup_data[guild_id][user_id]
            roles_to_add = [
                role for role_id in saved_role_ids
                if (role := member.guild.get_role(role_id)) and role != member.guild.default_role
            ]
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Khôi phục role cũ")
                print(f"[ROLE RESTORE] Đã khôi phục {len(roles_to_add)} role cho {member.name}")
        else:
            default_role = member.guild.get_role(DEFAULT_ROLE_ID)
            if default_role:
                await member.add_roles(default_role, reason="Role mặc định")
                print(f"[AUTO ROLE] Đã gắn role mặc định cho {member.name}")

        welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel:
            gif_file = discord.File("welcome.gif", filename="welcome.gif")
            embed = discord.Embed(
                title="🎉 Welcome!",
                description=f"Chào mừng {member.mention} đã tham gia **{member.guild.name}**!",
                color=0x00ff00,
            )
            embed.set_image(url="attachment://welcome.gif")
            embed.set_thumbnail(url=author_avatar_url(member))
            await welcome_channel.send(file=gif_file, embed=embed)
    except Exception as e:
        print(f"[MEMBER JOIN ERROR] {e}")


@bot.event
async def on_member_remove(member: discord.Member):
    """Khi member rời server - lưu roles"""
    try:
        roles_to_save = [role.id for role in member.roles if role != member.guild.default_role]
        if not roles_to_save:
            return
        backup_data = load_json(ROLES_BACKUP_FILE)
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        backup_data.setdefault(guild_id, {})[user_id] = roles_to_save
        save_json(ROLES_BACKUP_FILE, backup_data)
        print(f"[ROLE BACKUP] Đã lưu {len(roles_to_save)} role của {member.name}")
    except Exception as e:
        print(f"[ROLE BACKUP ERROR] {e}")


@bot.event
async def on_message_delete(message: discord.Message):
    await log_to_channel(message, "DELETED")


# =====================================================================
# GIVEAWAY
# =====================================================================
async def handle_giveaway_end(ga_message: discord.Message, end_time: datetime,
                               num_winners: int, prize: str):
    await asyncio.sleep((end_time - datetime.now(pytz.UTC)).total_seconds())
    ga_id = str(ga_message.id)
    if ga_id not in active_giveaways:
        print(f"[GA Info] Giveaway {ga_id} đã kết thúc hoặc bị hủy bỏ thủ công.")
        return

    try:
        ga_message = await ga_message.channel.fetch_message(ga_message.id)
    except discord.NotFound:
        print(f"[GA Error] Tin nhắn GA {ga_id} không tìm thấy.")
        del active_giveaways[ga_id]
        return

    reaction = discord.utils.find(
        lambda r: str(r.emoji) == "<:pepeOK:1233449603076984912>",
        ga_message.reactions
)
    participants = []
    if reaction:
        participants = [user async for user in reaction.users() if not user.bot]

    winners = []
    result_text = "hard"
    result_color = 0x7992da

    if participants:
        num_to_select = min(num_winners, len(participants))
        winners = random.sample(participants, num_to_select)

    if winners:
        winner_mentions = ", ".join(winner.mention for winner in winners)
        result_text = f"🎉 Chúc mừng {winner_mentions} đã thắng **{prize}**!"
    elif participants:
        result_text = "chê quà à?"

    ended_embed = discord.Embed(
        title=f"🎉 GIVEAWAY END: {prize}",
        description=result_text,
        color=result_color,
    )
    ended_embed.set_footer(text=f"Số người thắng: {num_winners} | Tham gia: {len(participants)}")

    await ga_message.edit(embed=ended_embed)
    await ga_message.channel.send(result_text)
    del active_giveaways[ga_id]


# =====================================================================
# ANTI-SCAM
# =====================================================================
async def handle_scam_channel(message: discord.Message):
    member = message.guild.get_member(message.author.id)
    if member is None:
        return

    immune_role = message.guild.get_role(IMMUNE_ROLE_ID)
    if immune_role is not None and immune_role in member.roles:
        print(f"[AUTO BAN] User {member.name} is immune to auto-timeout")
        return

    try:
        cutoff = datetime.now(pytz.UTC) - timedelta(minutes=5)
        for channel in message.guild.text_channels:
            try:
                async for msg in channel.history(limit=None, after=cutoff):
                    if msg.author.id == member.id:
                        await msg.delete()
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            except Exception as e:
                print(f"[DELETE MESSAGE ERROR in {channel.name}] {e}")

        await member.timeout(timedelta(days=28), reason="Scam detected in restricted channel")
        print(f"[AUTO BAN] User {member.name}#{member.discriminator} has been timed out for scam activity")
    except discord.Forbidden:
        print(f"[TIMEOUT ERROR] Bot không có quyền timeout {member.name}")
    except discord.HTTPException as e:
        print(f"[TIMEOUT ERROR] HTTP Exception: {e}")
    except Exception as e:
        print(f"[TIMEOUT ERROR] {e}")


# =====================================================================
# TEXT-TRIGGERED RESPONSES (keyword lookups)
# =====================================================================
async def handle_simple_responses(message: discord.Message, content: str) -> bool:
    """Returns True if a response was sent (so on_message can stop early if desired)."""
    if content in FILE_RESPONSES:
        await message.channel.send(file=discord.File(FILE_RESPONSES[content]))
        return True
    if content in GIF_RESPONSES:
        await message.channel.send(GIF_RESPONSES[content])
        return True
    if content in NEKOQT_PATTERNS:
        images = glob.glob(NEKOQT_PATTERNS[content])
        if images:
            await message.channel.send(file=discord.File(random.choice(images)))
        return True
    if content == "flop":
        await message.channel.send("<:flop:1397412530107711570>")
        return True
    return False


async def handle_reaction_keywords(message: discord.Message, content: str):
    if any(kw in content for kw in REACTION_KEYWORDS):
        try:
            await message.add_reaction("<:wut:1391968406143504466>")
        except Exception:
            pass


# =====================================================================
# neko* COMMAND HANDLERS (plain-text, no prefix — matches original behavior)
# =====================================================================
async def cmd_nekoroll(message: discord.Message, content: str):
    args = content.split()[1:]
    if not args:
        await message.channel.send("Nhập số.")
        return
    if args[0] == "help":
        embed = discord.Embed(
            title="Hướng dẫn sử dụng `nekoroll` 🎲",
            description="Dành cho mọi servers", color=0x29a8e0,
        )
        embed.add_field(name="nekoroll <x> <y>", value="Trả về số bất kỳ từ `<x>` đến `<y>`.", inline=False)
        await message.channel.send(embed=embed)
        return
    try:
        if len(args) == 1:
            x = int(args[0])
            await message.channel.send(f"`{random.randint(0, x)}`")
        else:
            x, y = int(args[0]), int(args[1])
            await message.channel.send(f"`{random.randint(x, y)}`")
    except ValueError:
        await message.channel.send("Hãy nhập khoảng hợp lệ.")


async def cmd_nekopick(message: discord.Message):
    args = message.content[9:].strip()
    if not args:
        await message.channel.send("`nekopick A,B`")
        return
    choices = [c.strip() for c in args.split(',') if c.strip()]
    if len(choices) < 2:
        await message.channel.send("ít nhất 2 lựa chọn.")
        return
    selected = random.choice(choices)
    emoji = random.choice(EMOJI_LIST)
    await message.channel.send(f"neko choose: **{selected}** {emoji}")


async def cmd_nekoexp(message: discord.Message, content: str):
    args = content.split()[1:]
    target_user = message.author
    if message.mentions:
        target_user = message.mentions[0]
    elif args and args[0].isdigit():
        found = message.guild.get_member(int(args[0]))
        if found:
            target_user = found

    exp_info = get_exp_info(target_user.id)
    embed = discord.Embed(title=f"📊 Thông tin EXP của {target_user.display_name}", color=0x29a8e0)
    embed.set_thumbnail(url=author_avatar_url(target_user))

    if exp_info["is_max"]:
        embed.add_field(name="🏆 Cấp độ", value=f"**Level {exp_info['level']} (MAX)**", inline=True)
        embed.add_field(name="💎 Total EXP", value=f"**{exp_info['exp']:,}**", inline=True)
        embed.add_field(name="✨ Tiến độ", value="**Congratulations** 🎉", inline=False)
    else:
        progress_bar_length = 20
        filled_length = int(progress_bar_length * exp_info["progress"] / 100)
        bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
        embed.add_field(name="🎯 Cấp độ", value=f"**Level {exp_info['level']}**", inline=True)
        embed.add_field(name="💎 Total EXP", value=f"**{exp_info['exp']:,}**", inline=True)
        embed.add_field(
            name="📈 Tiến độ đến Level tiếp theo",
            value=f"**{exp_info['progress']:.1f}%**\n`{bar}` \n{exp_info['current_exp']:,}/{exp_info['next_exp']:,} EXP",
            inline=False,
        )
        exp_remaining = exp_info['next_exp'] - exp_info['current_exp']
        embed.add_field(name="EXP còn lại", value=f"**{exp_remaining:,}** EXP", inline=True)

    embed.set_footer(text=f"Requested by {message.author.display_name}",
                      icon_url=author_avatar_url(message.author))
    await message.channel.send(embed=embed)


async def cmd_nekoroulette_rank(message: discord.Message, data: dict, uid: str):
    user_data = data.get(uid, {"total_uses": 0, "current_streak": 0, "high_score": 0})
    embed = discord.Embed(title=f"🎯 nekoroulette Stats - {message.author.display_name}", color=0xff6b6b)
    embed.set_thumbnail(url=author_avatar_url(message.author))
    embed.add_field(name="🎲 Tổng số lần chơi", value=f"**{user_data['total_uses']}** lần", inline=True)
    embed.add_field(name="🔥 Streak hiện tại", value=f"**{user_data['current_streak']}** lần", inline=True)
    embed.add_field(name="🏆 Record cao nhất", value=f"**{user_data['high_score']}** lần", inline=True)

    survival_rate = 0
    if user_data['total_uses'] > 0:
        deaths = user_data['total_uses'] - user_data['current_streak']
        survival_rate = ((user_data['total_uses'] - deaths) / user_data['total_uses']) * 100
    embed.add_field(name="📊 Tỷ lệ sống sót", value=f"**{survival_rate:.1f}%**", inline=True)

    if user_data['current_streak'] >= 10:
        risk_emoji, risk_text = "🔴", "Cực kỳ nguy hiểm"
    elif user_data['current_streak'] >= 5:
        risk_emoji, risk_text = "🟠", "Nguy hiểm"
    elif user_data['current_streak'] >= 3:
        risk_emoji, risk_text = "🟡", "Rủi ro"
    else:
        risk_emoji, risk_text = "🟢", "An toàn"
    embed.add_field(name=f"{risk_emoji} Mức độ rủi ro", value=f"**{risk_text}**", inline=True)

    embed.set_footer(text="💀 hard!", icon_url=bot_avatar_url())
    await message.channel.send(embed=embed)


async def cmd_nekoroulette_top(message: discord.Message, data: dict):
    sorted_users = []
    for user_id, user_data in data.items():
        if isinstance(user_data, dict) and user_data.get('high_score', 0) > 0:
            member = message.guild.get_member(int(user_id))
            if member:
                sorted_users.append((member, user_data))
    sorted_users.sort(key=lambda x: x[1]['high_score'], reverse=True)
    top_users = sorted_users[:10]

    embed = discord.Embed(
        title="🏆 nekoroulette Leaderboard - Top Survivors",
        description="*Top 10 in dead game*", color=0xffd700,
    )
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    if top_users:
        leaderboard_text = ""
        for i, (member, user_data) in enumerate(top_users):
            medal = medals[i] if i < len(medals) else f"{i + 1}."
            status = "🔥" if user_data.get('current_streak', 0) > 0 else "💀"
            leaderboard_text += f"{medal} **{member.display_name}** {status}\n"
            leaderboard_text += (
                f"     └ Record: **{user_data['high_score']}** | "
                f"Played: **{user_data.get('total_uses', 0)}** | "
                f"Current: **{user_data.get('current_streak', 0)}**\n\n"
            )
        embed.add_field(name="🎯 Top Survivors", value=leaderboard_text, inline=False)
    else:
        embed.add_field(name="😅 Chưa có ai chơi", value="Hãy là người đầu tiên thử thách vận may!", inline=False)

    embed.add_field(name="📝 Chú thích", value="🔥 = Đang trong streak | 💀 = Đã chết", inline=False)
    embed.set_footer(
        text=f"📊 Tổng {len(data)} người đã chơi • Cập nhật lúc {datetime.now().strftime('%H:%M')}",
        icon_url=bot_avatar_url(),
    )
    await message.channel.send(embed=embed)


async def cmd_nekoroulette(message: discord.Message, content: str):
    now_utc = datetime.now(pytz.UTC)
    uid = str(message.author.id)
    args = content.split()[1:]
    data = load_json(ROULETTE_FILE)

    if len(args) == 1 and args[0] in ("rank", "top"):
        if args[0] == "rank":
            await cmd_nekoroulette_rank(message, data, uid)
        else:
            await cmd_nekoroulette_top(message, data)
        return

    last_used = user_cooldowns.get(uid)
    if last_used and (now_utc - last_used).total_seconds() < ROULETTE_COOLDOWN_SECONDS:
        msg = await message.channel.send("<:luom:1391968383393726534> vội thế à")
        await asyncio.sleep(2)
        await msg.delete()
        return
    user_cooldowns[uid] = now_utc

    if len(args) != 1 or not args[0].isdigit():
        return
    choice = int(args[0])
    if not 1 <= choice <= 6:
        await message.channel.send("Chọn số từ 1 đến 6.")
        return

    user_data = data.get(uid, {"total_uses": 0, "last_timeout": None,
                                "current_streak": 0, "high_score": 0})

    if user_data["last_timeout"]:
        last = pytz.UTC.localize(datetime.fromisoformat(user_data["last_timeout"]))
        if now_utc - last < timedelta(hours=2):
            await message.channel.send("Bạn đang bị timeout.")
            return

    suspense_msg = await message.channel.send("Bạn khá là....")
    await asyncio.sleep(2)
    bullet = random.randint(1, 6)
    user_data["total_uses"] += 1

    if choice == bullet:
        user_data["last_timeout"] = now_utc.isoformat()
        user_data["current_streak"] = 0
        data[uid] = user_data
        save_json(ROULETTE_FILE, data)
        try:
            await message.author.timeout(timedelta(hours=2), reason="Trúng đạn trong nekoroulette 🎯")
            await suspense_msg.edit(
                content="Bạn không được may mắn lắm thì phải..... "
                        "<:HarukaSalute:1398351733767278742> <:HarukaSalute:1398351733767278742>"
            )
        except Exception as e:
            await suspense_msg.edit(content=f"❌ Không thể timeout: `{e}`")
    else:
        user_data["current_streak"] += 1
        user_data["high_score"] = max(user_data["high_score"], user_data["current_streak"])
        data[uid] = user_data
        save_json(ROULETTE_FILE, data)
        await suspense_msg.edit(content="Bạn khá là may mắn đó <:UmiSip:1398351745779892325>")


async def cmd_nekohelp(message: discord.Message):
    embed = discord.Embed(
        title="<:UmiWink:1401555090396942458> neko Bot - Hướng dẫn sử dụng",
        description="*Chào mừng bạn đến với thế giới của neko!* <:HarukaSalute:1398351733767278742>",
        color=0x29a8e0,
    )
    embed.set_thumbnail(url=bot_avatar_url())
    embed.add_field(
        name="🎮 **GAME & GIẢI TRÍ**",
        value=("`nekoroll <số>` - Random từ 0 đến số đó\n"
               "`nekoroll <x> <y>` - Random từ x đến y\n"
               "`nekopick A,B,C` - Chọn ngẫu nhiên từ danh sách"),
        inline=False,
    )
    embed.add_field(
        name="🎯 **RUSSIAN ROULETTE**",
        value=("`nekoroulette <1-6>` - Chơi súng lục ổ quay \n"
               "`nekoroulette rank` - Xem thống kê cá nhân\n"
               "`nekoroulette top` - Bảng xếp hạng top 10"),
        inline=False,
    )
    embed.add_field(
        name="📊 **HỆ THỐNG LEVEL**",
        value="`nekoexp` - Xem EXP và tiến độ của bạn\n`nekoexp @user` - Xem EXP của người khác",
        inline=False,
    )
    base_cmds = ['nekoroll', 'nekopick', 'nekoroulette', 'nekoexp', 'nekohelp']
    extra = 2 if message.author.guild_permissions.moderate_members else 0
    embed.set_footer(
        text=f"🌊 Made with 💙 by neko • {len(base_cmds) + extra} commands available",
        icon_url=author_avatar_url(message.author),
    )
    await message.channel.send(embed=embed)


async def cmd_nekomute(message: discord.Message, content: str):
    if not message.author.guild_permissions.moderate_members:
        await message.channel.send("nhiễu.")
        return
    args = content.split()
    if len(args) < 3:
        return
    if not message.mentions:
        await message.channel.send("ai thế? ")
        return
    target = message.mentions[0]
    minutes = int(args[2]) if args[2].isdigit() else 10
    reason = " ".join(args[3:]) if len(args) > 3 else "Không có lý do"

    try:
        if str(target.id) in PROTECTED_MUTE_IDS:
            await message.author.timeout(timedelta(minutes=minutes), reason="adu tạo phản <:__:1391968369867096104>")
            await message.channel.send("adu tạo phản <:__:1391968369867096104>  ")
            return
        await target.timeout(timedelta(minutes=minutes), reason=reason)
        await message.channel.send(
            f" <:hmmh:1402863680722571326> Đã nín {target.mention} trong {minutes} phút. Lý do: {reason}"
        )
    except Exception as e:
        await message.channel.send(f"❌ Lỗi khi mute: {e}")


async def cmd_nekolock(message: discord.Message, lock: bool):
    if not message.author.guild_permissions.manage_channels:
        await message.channel.send("<:job:1404855007169351732>.")
        return
    try:
        overwrite = message.channel.overwrites_for(message.guild.default_role)
        overwrite.send_messages = False if lock else None
        reason = f"{'Khóa' if lock else 'Mở khóa'} kênh bởi {message.author.display_name}"
        await message.channel.set_permissions(message.guild.default_role, overwrite=overwrite, reason=reason)
        await message.channel.send("Đã khóa" if lock else "Đã mở khóa.")
    except discord.Forbidden:
        await message.channel.send("❌ Bot không có đủ quyền để thao tác trên kênh này. Hãy kiểm tra lại quyền hạn của bot.")
    except Exception as e:
        await message.channel.send(f"❌ Lỗi: {e}")


async def cmd_nekoga(message: discord.Message, content: str):
    if not message.author.guild_permissions.manage_channels:
        await message.channel.send("❌ Bạn cần quyền **Quản lý Kênh** để tạo Giveaway.")
        return
    args = content.split()[1:]
    if len(args) < 2:
        await message.channel.send("Sử dụng: `nekoga <tên_GA> <thời_gian_phút> [số_người_thắng: mặc định 1]`")
        return

    prize = args[0]
    try:
        duration_minutes = int(args[1])
        if duration_minutes <= 0:
            await message.channel.send("Thời gian phải lớn hơn 0 phút.")
            return
    except ValueError:
        await message.channel.send("Thời gian phải là số nguyên (phút).")
        return

    num_winners = 1
    if len(args) > 2:
        try:
            num_winners = int(args[2])
            if num_winners <= 0:
                await message.channel.send("Số người thắng phải lớn hơn 0.")
                return
        except ValueError:
            await message.channel.send("Số người thắng phải là số nguyên.")
            return

    end_time_ga = datetime.now(pytz.UTC) + timedelta(minutes=duration_minutes)
    embed = discord.Embed(
        title="<:Hehe:1233447270373134447> GIVEAWAY ",
        description=f"\n\n{prize}\n**WINNER:** {num_winners}\n**END:** {discord.utils.format_dt(end_time_ga, 'R')}",
        color=0x7992da,
    )
    embed.set_footer(text=f"Tạo bởi: {message.author.display_name}", icon_url=author_avatar_url(message.author))
    ga_message = await message.channel.send(embed=embed)
    await ga_message.add_reaction("<:pepeOK:1233449603076984912>")

    active_giveaways[str(ga_message.id)] = {
        "channel_id": message.channel.id,
        "end_time": end_time_ga,
        "prize": prize,
        "winners": num_winners,
    }
    bot.loop.create_task(handle_giveaway_end(ga_message, end_time_ga, num_winners, prize))
    try:
        await message.delete()
    except Exception:
        pass


async def cmd_nekoban(message: discord.Message, content: str):
    if message.guild is None:
        return
    if not message.author.guild_permissions.ban_members:
        await message.channel.send("lượn")
        return
    if not message.guild.me.guild_permissions.ban_members:
        await message.channel.send("hard.")
        return

    args = content.split()
    if len(args) < 2 and not message.mentions:
        return

    target = None
    if message.mentions:
        target = message.mentions[0]
    elif args[1].isdigit():
        target = message.guild.get_member(int(args[1]))

    if target is None:
        await message.channel.send("ai thế? ")
        return
    if target == message.author or target == message.guild.owner:
        await message.channel.send("?")
        return
    if target.top_role >= message.guild.me.top_role:
        await message.channel.send("adu tạo phản<:__:1391968369867096104>.")
        return

    reason = " ".join(args[2:]).strip() if len(args) > 2 else "No reason"
    try:
        await target.ban(reason=reason)
        await message.channel.send(f"Đã ban {target.mention}")
    except Exception as e:
        await message.channel.send(f"❌ Lỗi khi ban: {e}")


async def cmd_nekotime(message: discord.Message):
    if message.guild is None:
        return
    diff = get_countdown_diff()
    if diff.total_seconds() > 0:
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        file_path = create_countdown_card(days, hours, minutes)
        try:
            await message.channel.send(file=discord.File(file_path))
        finally:
            os.remove(file_path)
    else:
        await message.channel.send("🎉 Đã đến ngày mục tiêu!")


# =====================================================================
# MAIN MESSAGE DISPATCH
# =====================================================================
NEKO_COMMANDS = {
    "nekoroll": cmd_nekoroll,
    "nekopick": None,   # handled specially (needs raw message.content, not lowercased)
    "nekoexp": cmd_nekoexp,
    "nekoroulette": cmd_nekoroulette,
    "nekomute": cmd_nekomute,
    "nekoga": cmd_nekoga,
}


@bot.event
async def on_message(message: discord.Message):
    await log_to_channel(message, "NEW")

    if message.author.bot:
        return

    if message.channel.id == SCAM_CHANNEL_ID:
        await handle_scam_channel(message)

    content = message.content.lower().strip()

    # Simple keyword -> file/gif/emoji responses
    await handle_simple_responses(message, content)
    await handle_reaction_keywords(message, content)

    # EXP gain (rate-limited per user)
    now_utc = datetime.now(pytz.UTC)
    uid = str(message.author.id)
    if uid not in last_exp_time or (now_utc - last_exp_time[uid]).total_seconds() >= EXP_COOLDOWN:
        exp_gain = random.randint(EXP_MIN, EXP_MAX)
        bonus_role = message.guild.get_role(BONUS_ROLE_ID) if message.guild else None
        if bonus_role and bonus_role in message.author.roles:
            exp_gain *= 2
        await add_exp(message.author, exp_gain)
        last_exp_time[uid] = now_utc

    # Random emoji chatter
    if random.random() < 0.015:
        await message.channel.send(random.choice(EMOJI_LIST))

    # neko* text commands (plain text, no bot prefix — matches original design)
    if content.startswith("nekoroll"):
        await cmd_nekoroll(message, content)
    elif content.startswith("nekopick"):
        await cmd_nekopick(message)
    elif content.startswith("nekoexp"):
        await cmd_nekoexp(message, content)
    elif content.startswith("nekoroulette"):
        await cmd_nekoroulette(message, content)
    elif content.startswith("nekohelp"):
        await cmd_nekohelp(message)
    elif content.startswith("nekomute"):
        await cmd_nekomute(message, content)
    elif content.startswith("nekolock"):
        await cmd_nekolock(message, lock=True)
    elif content.startswith("nekounlock"):
        await cmd_nekolock(message, lock=False)
    elif content.startswith("nekoga"):
        await cmd_nekoga(message, content)
    elif content.startswith(("nekoban", "^nekoban")):
        await cmd_nekoban(message, content)
    elif content.startswith(("nekotime", "^nekotime")):
        await cmd_nekotime(message)

    log_message_to_file(message)
    await bot.process_commands(message)


# =====================================================================
# SLASH COMMANDS
# =====================================================================
@tree.command(name="active", description="check")
async def active_dev(interaction: discord.Interaction):
    await interaction.response.send_message("dev active")


# =====================================================================
# ENTRYPOINT
# =====================================================================
if __name__ == "__main__":
    load_dotenv()
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        raise SystemExit("❌ Thiếu biến môi trường DISCORD_TOKEN.")
    bot.run(DISCORD_TOKEN)
