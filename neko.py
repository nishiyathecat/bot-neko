import discord
from discord.ext import commands
import random
import asyncio
import json
import os
import glob
from datetime import datetime, timedelta, time
import pytz

def log_message_to_file(message: discord.Message, log_path="messages.log"):
    with open(log_path, "a", encoding="utf8") as log_file:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{time_str}] {message.guild.name if message.guild else 'DM'} #{message.channel} | {message.author.name}: {message.content}\n")

# ==== CONFIG ====
SCAM_CHANNEL_ID = 1403567670229729423
IMMUNE_ROLE_ID = 1386995499306848310
BONUS_ROLE_ID = 1237698075989114942
LOG_CHANNEL_ID = 1449020423663783936
ROLE_LEVELS = [
    1403605505590689885,
    1403605764831969371,
    1403605883262341240,
    1403606299735756840,
    1403605754056806450,
    1403606581937049740,
    1403606476077011035
]
LEVEL_EXP = [100, 3000, 11000, 18000, 28000, 38000, 50000]
EXP_COOLDOWN = 15
EXP_MIN = 3
EXP_MAX = 9

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="^", intents=intents)
tree = bot.tree

active_giveaways = {}

vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
CHANNEL_ID = 1233440140748128288
#---- LOGGING FUNCTION ----
async def log_to_channel(message: discord.Message, action: str):
    """Gửi nội dung tin nhắn và đính kèm (nếu có) đến kênh nhật ký."""
    
    # Bỏ qua nếu tin nhắn là DM hoặc tác giả là bot
    if message.author.bot or not message.guild:
        return

    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        print(f"[LOG ERROR] Không tìm thấy kênh Log với ID: {LOG_CHANNEL_ID}")
        return
        
    # 1. Định dạng Embed
    embed = discord.Embed(
        title=f"[{action}] Tin nhắn {message.author.display_name}",
        description=message.content if message.content else "*Không có nội dung văn bản*",
        color=discord.Color.blue() if action == "NEW" else discord.Color.red() if action == "DELETED" else discord.Color.yellow()
    )
    embed.set_author(name=f"{message.author.display_name} ({message.author.id})", 
                     icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
    embed.add_field(name="Kênh Gốc", value=message.channel.mention, inline=False)
    embed.set_footer(text=f"ID tin nhắn: {message.id}")
    
    # 2. Xử lý File đính kèm (Attachments)
    attachment_files = []
    attachment_urls = []
    
    for attachment in message.attachments:
        if attachment.size < 8 * 1024 * 1024: # Dưới 8MB
            try:
                temp_file = await attachment.to_file()
                attachment_files.append(temp_file)
            except Exception as e:
                attachment_urls.append(attachment.url)
        else:
            attachment_urls.append(attachment.url)
    
    # 3. Gửi Embed
    await log_channel.send(embed=embed, files=attachment_files if attachment_files else None)
    
    # Gửi URL cho các file quá lớn hoặc lỗi tải
    if attachment_urls:
        url_list = "\n".join(attachment_urls)
        await log_channel.send(f"**[Attachments/Large Files from {message.channel.mention}]**\n{url_list}")

async def schedule_message_weekly(bot, channel_id, target_day_of_week: int, send_time: time, message_content: str):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now(vn_tz)
        days_until_target = (target_day_of_week - now.weekday() + 7) % 7
        target_time = now.replace(hour=send_time.hour, minute=send_time.minute, second=0, microsecond=0)
        next_send_time = now + timedelta(days=days_until_target)
        next_send_time = next_send_time.replace(hour=send_time.hour, minute=send_time.minute, second=0, microsecond=0)
        if days_until_target == 0 and now > target_time:
            next_send_time = next_send_time + timedelta(days=7)
        wait_seconds = (next_send_time - now).total_seconds()
        
        await asyncio.sleep(wait_seconds)
        
        channel = bot.get_channel(channel_id)
        if channel:
            content_lower = message_content.lower()
            
            if content_lower.endswith(('.png', '.jpg', '.gif')):
                try:
                    await channel.send(file=discord.File(message_content))
                except FileNotFoundError:
                    await channel.send(f"❌ Lỗi: Không tìm thấy file `{message_content}` trong thư mục.")
                except Exception as e:
                    await channel.send(f"❌ Lỗi gửi file: {e}")
            elif message_content and message_content.strip():
                await channel.send(message_content)
        
        await asyncio.sleep(1)

async def schedule_message(channel_id, send_time, message_content):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now(vn_tz)
        target = now.replace(hour=send_time.hour, minute=send_time.minute, second=0, microsecond=0)
        
        if now > target:
            from datetime import timedelta
            target = target + timedelta(days=1)
            
        wait_seconds = (target - now).total_seconds()
        
        await asyncio.sleep(wait_seconds)
        channel = bot.get_channel(channel_id)
        if channel:
            content_lower = message_content.lower()
            
            if content_lower.endswith(('.png', '.jpg', '.gif')):
                try:
                    await channel.send(file=discord.File(message_content))
                except FileNotFoundError:
                    await channel.send(f"❌ Lỗi: Không tìm thấy file `{message_content}` trong thư mục.")
                except Exception as e:
                    await channel.send(f"❌ Lỗi gửi file: {e}")
            elif message_content and message_content.strip():

                await channel.send(message_content)
                

        await asyncio.sleep(1)
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    await tree.sync()
    
    bot.loop.create_task(schedule_message(CHANNEL_ID, time(0, 0), "https://tenor.com/view/osaka-azuman-goodnight-gn-sleep-gif-24066064"))
    bot.loop.create_task(schedule_message(CHANNEL_ID, time(3, 0), "https://tenor.com/view/blend-s-bathroom-banio-trap-anime-gif-10374444 "))
    bot.loop.create_task(schedule_message(CHANNEL_ID, time(6, 0), "https://tenor.com/view/little-witch-academia-good-morning-gif-24763182"))
    bot.loop.create_task(schedule_message_weekly(bot, CHANNEL_ID,0,time(7,0),"https://tenor.com/view/monday-konata-alkruhn-monday-moment-gif-25525919"))
    bot.loop.create_task(schedule_message_weekly(bot, CHANNEL_ID,6,time(21,0),"Sunday.png"))
    
@tree.command(name="active", description="check")
async def active_dev(interaction: discord.Interaction):
    await interaction.response.send_message("dev active")


roulette_file = "umiroulette_data.json"
exp_file = "exp_data.json"
roles_backup_file = "roles_backup.json"

for file in [roulette_file, exp_file, roles_backup_file]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# ==== EMOJIS ====
emoji_list = [
    "<:AoLewd:1398351742789226636>", "<:doropium:1398351738108641290>",
    "<:ShikiSmug:1398351730181411088>", "<:UmiSip:1398351745779892325>",
    "<:UmiEmbarrassed:1398351749361832089>", "<:nice:1391968396387549224>",
    "<:wut:1391968406143504466>", "<:dorothy:1393268584536342548>",
    "<:HarukaSalute:1398351733767278742>","<a:nod:1404327366490329169>"
]

last_exp_time = {}

async def add_exp(member: discord.Member, amount: int):
    data = load_json(exp_file)
    uid = str(member.id)
    
    if uid not in data:
        data[uid] = {"exp": 0, "level": 1}
    elif isinstance(data[uid], int):
        old_exp = data[uid]
        data[uid] = {"exp": old_exp, "level": 1}
        
        for i in range(len(LEVEL_EXP)-1, -1, -1):
            if data[uid]["exp"] >= LEVEL_EXP[i]:
                data[uid]["level"] = i+1
                break

    data[uid]["exp"] += amount
    
    for i in range(len(LEVEL_EXP)-1, -1, -1):
        if data[uid]["exp"] >= LEVEL_EXP[i]:
            if data[uid]["level"] != i+1:
                old_level = data[uid]["level"]
                data[uid]["level"] = i+1
                
                for rid in ROLE_LEVELS:
                    role = member.guild.get_role(rid)
                    if role in member.roles:
                        await member.remove_roles(role)
                
                new_role = member.guild.get_role(ROLE_LEVELS[i])
                if new_role:
                    await member.add_roles(new_role)
                    await member.send(f"🎉 Chúc mừng! Bạn đã lên cấp **{i+1}** và nhận role **{new_role.name}**!")
            break

    save_json(exp_file, data)

def get_exp_info(user_id: str):
    """Lấy thông tin EXP và tính % tiến độ"""
    data = load_json(exp_file)
    uid = str(user_id)

    if uid not in data:
        return {"exp": 0, "level": 1, "progress": 0.0, "current_exp": 0, "next_exp": LEVEL_EXP[1]}

    user_data = data[uid]

    if isinstance(user_data, int):
        exp = user_data
        level = 1
        for i in range(len(LEVEL_EXP)-1, -1, -1):
            if exp >= LEVEL_EXP[i]:
                level = i+1
                break
    else:
        exp = user_data["exp"]
        level = user_data["level"]

    if level >= len(LEVEL_EXP):
        return {
            "exp": exp,
            "level": level,
            "progress": 100.0,
            "current_exp": exp,
            "next_exp": exp,
            "is_max": True
        }

    current_level_exp = LEVEL_EXP[level-1]
    next_level_exp = LEVEL_EXP[level]
    exp_needed = next_level_exp - current_level_exp
    exp_gained = exp - current_level_exp
    progress = (exp_gained / exp_needed) * 100 if exp_needed > 0 else 100

    return {
        "exp": exp,
        "level": level,
        "progress": progress,
        "current_exp": exp_gained,
        "next_exp": exp_needed,
        "is_max": False
    }


@bot.event
async def on_member_join(member: discord.Member):
    """Khi member join - gắn role VÀ gửi welcome"""
    
    DEFAULT_ROLE_ID = 1237644257934704713
    WELCOME_CHANNEL_ID = 1233453277207859232
    
@bot.event
async def on_member_join(member: discord.Member):
    """Khi member join - gắn role VÀ gửi welcome"""
    
    DEFAULT_ROLE_ID = 1237644257934704713
    WELCOME_CHANNEL_ID = 1233453277207859232
    
    try:

        backup_data = load_json(roles_backup_file)
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        
        # Khôi phục role nếu có dữ liệu backup
        if guild_id in backup_data and user_id in backup_data[guild_id]:
            saved_role_ids = backup_data[guild_id][user_id]
            roles_to_add = []
            
            for role_id in saved_role_ids:
                role = member.guild.get_role(role_id)
                # Đảm bảo role tồn tại và không phải là role @everyone mặc định
                if role and role != member.guild.default_role:
                    roles_to_add.append(role)
            
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Khôi phục role cũ")
                print(f"[ROLE RESTORE] Đã khôi phục {len(roles_to_add)} role cho {member.name}")
        # Gán role mặc định nếu không có dữ liệu backup
        else:
            default_role = member.guild.get_role(DEFAULT_ROLE_ID)
            if default_role:
                await member.add_roles(default_role, reason="Role mặc định")
                print(f"[AUTO ROLE] Đã gắn role mặc định cho {member.name}") # Log chỉ nên chạy khi gắn role
                
        # 2. Gửi welcome
        welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel:
            
            gif_file = discord.File("welcome.gif", filename="welcome.gif") 
            
            embed = discord.Embed(
                title="🎉 Welcome!",
                description=f"Chào mừng {member.mention} đã tham gia **{member.guild.name}**!",
                color=0x00ff00
            )
            
            embed.set_image(url="attachment://welcome.gif")
            
            # Kiểm tra `member.avatar` không phải là `None`
            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            embed.set_thumbnail(url=avatar_url)
            
            await welcome_channel.send(file=gif_file, embed=embed)
            
    except Exception as e:
        print(f"[MEMBER JOIN ERROR] {e}")

# ---

@bot.event
async def on_member_remove(member: discord.Member):
    """Khi member rời server - lưu roles"""
    try:
        roles_to_save = [role.id for role in member.roles if role != member.guild.default_role]
        if not roles_to_save:
            return
            

        backup_data = load_json(roles_backup_file)
        guild_id = str(member.guild.id)
        user_id = str(member.id)
        
        if guild_id not in backup_data:
            backup_data[guild_id] = {}
            
        backup_data[guild_id][user_id] = roles_to_save
        save_json(roles_backup_file, backup_data)
        print(f"[ROLE BACKUP] Đã lưu {len(roles_to_save)} role của {member.name}")
        
    except Exception as e:
        print(f"[ROLE BACKUP ERROR] {e}")
        
# --- Hàm xử lý kết thúc Giveaway ---
async def handle_giveaway_end(ga_message: discord.Message, end_time: datetime, num_winners: int, prize: str):
    await asyncio.sleep((end_time - datetime.now(pytz.UTC)).total_seconds())

    # Xử lý khi hết giờ
    ga_id = str(ga_message.id)
    if ga_id in active_giveaways:
        
        # Tải lại tin nhắn để lấy reaction mới nhất
        try:
            ga_message = await ga_message.channel.fetch_message(ga_message.id)
        except discord.NotFound:
            print(f"[GA Error] Tin nhắn GA {ga_id} không tìm thấy.")
            del active_giveaways[ga_id]
            return
        
        reaction = discord.utils.get(ga_message.reactions, emoji="<:PepeOK:830759308459114546>")
        participants = []

        if reaction:
            # Lấy danh sách người đã reaction, loại bỏ bot
            users = await reaction.users().flatten()
            participants = [user for user in users if not user.bot]

        winners = []
        
        # --- BẮT ĐẦU PHẦN SỬA LỖI: Thiết lập giá trị mặc định ---
        result_text = "hard"
        result_color = 0x7992da
        
        if participants:
            # Chọn ngẫu nhiên người thắng
            num_to_select = min(num_winners, len(participants))
            winners = random.sample(participants, num_to_select)

        # --- Cập nhật Embed Kết thúc ---
        if winners:
            winner_mentions = ", ".join([winner.mention for winner in winners])
            result_text = f"🎉 Chúc mừng {winner_mentions} đã thắng **{prize}**!"
            result_color =  0x7992da
        elif participants: # Trường hợp này không nên xảy ra nếu logic chọn người thắng đúng, nhưng vẫn để để đảm bảo xử lý.
            result_text = "chê quà à?"
            result_color = 0x7992da

        # Cập nhật Embed
        ended_embed = discord.Embed(
            title=f"🎉 GIVEAWAY END: {prize}",
            description=result_text, # Dòng này giờ luôn có giá trị
            color=result_color
        )
        ended_embed.set_footer(text=f"Số người thắng: {num_winners} | Tham gia: {len(participants)}")
        
        await ga_message.edit(embed=ended_embed)
        await ga_message.channel.send(result_text)
        
        # Xóa khỏi danh sách hoạt động
        del active_giveaways[ga_id]
    else:
        # Trường hợp bot bị restart và GA đã được xóa khỏi bộ nhớ nhưng vẫn chạy tác vụ
        print(f"[GA Info] Giveaway {ga_id} đã kết thúc hoặc bị hủy bỏ thủ công.")
# ==== ON MESSAGE ====
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ==== AUTO BAN SCAM ====
    if message.channel.id == SCAM_CHANNEL_ID:
        member = message.guild.get_member(message.author.id)
        if member is None:
            return
        immune_role = message.guild.get_role(IMMUNE_ROLE_ID)
        if immune_role is None or (immune_role is not None and immune_role in member.roles):
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
            timeout_duration = timedelta(days=28)
            await member.timeout(timeout_duration, reason="Scam detected in restricted channel")
            print(f"[AUTO BAN] User {member.name}#{member.discriminator} has been timed out for scam activity")
        except discord.Forbidden:
            print(f"[TIMEOUT ERROR] Bot không có quyền timeout {member.name}")
        except discord.HTTPException as e:
            print(f"[TIMEOUT ERROR] HTTP Exception: {e}")
        except Exception as e:
            print(f"[TIMEOUT ERROR] {e}")
    
    if message.content.lower().strip() == "simp":
        await message.channel.send(file=discord.File("simp.jpg"))
    if message.content.lower().strip() == "khó":
        await message.channel.send(file=discord.File("khó.png"))
    if message.content.lower().strip() == "vl":
        await message.channel.send(file=discord.File("vl.png"))
    if message.content.lower().strip() == "sybau":
        await message.channel.send(file=discord.File("sybau.jpg"))
    if message.content.lower().strip() == "chọn đi":
        await message.channel.send(file=discord.File("chon.png"))
    if message.content.lower().strip() == "hi chat":
        await message.channel.send(file=discord.File("hi.gif"))
    if message.content.lower().strip() == "thoát khỏi lớp da thịt":
        await message.channel.send(file=discord.File("thit.png"))
    if message.content.lower().strip() == "fembi":
        await message.channel.send(file=discord.File("fembi.png"))    
    # gif
    if message.content.lower().strip() == "pat pat":
        await message.channel.send("https://tenor.com/view/shiro-anime-no-game-no-life-headpat-cute-gif-17317343567086759130")
    if message.content.lower().strip() == "pat":
        await message.channel.send("https://tenor.com/view/anime-pat-anime-gif-26506449 ")
    if message.content.lower().strip() == "hmph":
        await message.channel.send("https://tenor.com/view/nananiji-hm-hmm-hmph-eh-gif-4830821874963593839")
    if message.content.lower().strip() == "nekogn":
        await message.channel.send("https://tenor.com/view/osaka-azuman-goodnight-gn-sleep-gif-24066064")
    if message.content.lower().strip() == "nekogm":
        await message.channel.send("https://tenor.com/view/little-witch-academia-good-morning-gif-24763182")
    if message.content.lower().strip() == "owo":
        await message.channel.send("https://tenor.com/view/kanna-kamui-kobayashis-dragon-maid-anime-sparkling-eyes-gif-16297310")
    if message.content.lower().strip() == "yuri":
        await message.channel.send("https://giphy.com/embed/OGXilB8foNFIs")
    if message.content.lower().strip() == "bye bye":
        await message.channel.send("https://tenor.com/view/anime-bye-bye-maki-wave-soredemo-ayumu-wa-yosetekuru-when-will-ayumu-make-his-move-gif-26195508") 
    if message.content.lower().strip() == "time":
        await message.channel.send("https://tenor.com/view/tik-tok-meme-waiting-wait-time-gif-16450082290173148616") 
    if message.content.lower().strip() == "study":
        await message.channel.send("https://tenor.com/view/dragon-maid-kanna-eraser-anime-homework-gif-886305399648227690")
    if message.content.lower().strip() == "angry":
        await message.channel.send("https://tenor.com/view/angry-thiago-mad-angry-fist-emoji-gif-17761307")
    if message.content.lower().strip() == "exam":
        await message.channel.send("https://tenor.com/view/madara-uchiha-padai-learning-anime-uchiha-gif-10063372275053411217") 
    
    
    if message.content.lower().strip() == "nekoqt nishiya":
        images = glob.glob("nishiya*.jpg")
        if images:
            image_path = random.choice(images)
            await message.channel.send(file=discord.File(image_path))  
    if message.content.lower().strip() == "nekoqt bin":
        images = glob.glob("bin*.jpg")
        if images:
            image_path = random.choice(images)
            await message.channel.send(file=discord.File(image_path))
    if message.content.lower().strip() == "nekoqt vinh":
        images = glob.glob("vinh*.png")
        if images:
            image_path = random.choice(images)
            await message.channel.send(file=discord.File(image_path))
    
    keywords = ["nishi", "admin", "nishiya"]
    if any(kw in message.content.lower() for kw in keywords):
        try:
            await message.add_reaction("<:wut:1391968406143504466>")
        except:
            pass
    
    if message.content.lower().strip() == "flop":
        await message.channel.send("<:flop:1397412530107711570>")

    now = datetime.now(pytz.UTC)
    uid = str(message.author.id)
    if uid not in last_exp_time or (now - last_exp_time[uid]).total_seconds() >= EXP_COOLDOWN:
        exp_gain = random.randint(EXP_MIN, EXP_MAX)
        bonus_role = message.guild.get_role(BONUS_ROLE_ID)
        if bonus_role and bonus_role in message.author.roles:
            exp_gain *= 2
        await add_exp(message.author, exp_gain)
        last_exp_time[uid] = now

    if random.random() < 0.015:
        emoji = random.choice(emoji_list)
        await message.channel.send(emoji)

    content = message.content.lower().strip()
    data = load_json(roulette_file)

    if content.startswith("nekoroll"):
        args = content.split()[1:]
        if len(args) == 0:
            await message.channel.send("Nhập số.")
        elif args[0] == "help":
            embed = discord.Embed(title="Hướng dẫn sử dụng `nekoroll` 🎲", description="Dành cho mọi servers", color=0x29a8e0)
            embed.add_field(name="nekoroll <x> <y>", value="Trả về số bất kỳ từ `<x>` đến `<y>`.", inline=False)
            await message.channel.send(embed=embed)
        else:
            try:
                if len(args) == 1:
                    x = int(args[0])
                    await message.channel.send(f"`{random.randint(0, x)}`")
                else:
                    x = int(args[0])
                    y = int(args[1])
                    await message.channel.send(f"`{random.randint(x, y)}`")
            except:
                await message.channel.send("Hãy nhập khoảng hợp lệ.")

    elif content.startswith("nekopick"):
        args = message.content[9:].strip()
        if not args:
            await message.channel.send("`nekopick A,B`")
            return
        choices = [c.strip() for c in args.split(',') if c.strip()]
        if len(choices) < 2:
            await message.channel.send("ít nhất 2 lựa chọn.")
            return
        selected = random.choice(choices)
        emoji = random.choice(emoji_list)
        await message.channel.send(f"neko choose: **{selected}** {emoji}")

    elif content.startswith("nekoexp"):
        args = content.split()[1:]
        target_user = message.author
        if message.mentions:
            target_user = message.mentions[0]
        elif len(args) > 0 and args[0].isdigit():
            try:
                target_user = message.guild.get_member(int(args[0]))
                if not target_user:
                    await message.channel.send("not found.")
                    return
            except:
                pass
        exp_info = get_exp_info(target_user.id)
        embed = discord.Embed(
            title=f"📊 Thông tin EXP của {target_user.display_name}",
            color=0x29a8e0
        )
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
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
            embed.add_field(name="📈 Tiến độ đến Level tiếp theo", value=f"**{exp_info['progress']:.1f}%**\n`{bar}` \n{exp_info['current_exp']:,}/{exp_info['next_exp']:,} EXP", inline=False)
            exp_remaining = exp_info['next_exp'] - exp_info['current_exp']
            embed.add_field(name=" EXP còn lại", value=f"**{exp_remaining:,}** EXP", inline=True)
        embed.set_footer(text=f"Requested by {message.author.display_name}", icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        await message.channel.send(embed=embed)

    elif content.startswith("nekoroulette"):
        user_cooldowns = getattr(bot, '_user_cooldowns', {})
        COOLDOWN_SECONDS = 3
        now = datetime.now(pytz.UTC)
        uid = str(message.author.id)
        last_used = user_cooldowns.get(uid)
        args = content.split()[1:]
        if len(args) == 1 and args[0] in ["rank", "top"]:
            if args[0] == "rank":
                user_data = data.get(uid, {"total_uses": 0, "current_streak": 0, "high_score": 0})
                embed = discord.Embed(title=f"🎯 nekoroulette Stats - {message.author.display_name}", color=0xff6b6b)
                embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
                embed.add_field(name="🎲 Tổng số lần chơi", value=f"**{user_data['total_uses']}** lần", inline=True)
                embed.add_field(name="🔥 Streak hiện tại", value=f"**{user_data['current_streak']}** lần", inline=True)
                embed.add_field(name="🏆 Record cao nhất", value=f"**{user_data['high_score']}** lần", inline=True)
                survival_rate = 0
                if user_data['total_uses'] > 0:
                    deaths = user_data['total_uses'] - user_data['current_streak']
                    survival_rate = ((user_data['total_uses'] - deaths) / user_data['total_uses']) * 100
                embed.add_field(name="📊 Tỷ lệ sống sót", value=f"**{survival_rate:.1f}%**", inline=True)
                risk_emoji = "🟢"
                risk_text = "An toàn"
                if user_data['current_streak'] >= 10:
                    risk_emoji = "🔴"
                    risk_text = "Cực kỳ nguy hiểm"
                elif user_data['current_streak'] >= 5:
                    risk_emoji = "🟠"
                    risk_text = "Nguy hiểm"
                elif user_data['current_streak'] >= 3:
                    risk_emoji = "🟡"
                    risk_text = "Rủi ro"
                embed.add_field(name=f"{risk_emoji} Mức độ rủi ro", value=f"**{risk_text}**", inline=True)
                embed.set_footer(text="💀 hard!", icon_url=bot.user.avatar.url)
                await message.channel.send(embed=embed)
            elif args[0] == "top":
                sorted_users = []
                for user_id, user_data in data.items():
                    if isinstance(user_data, dict) and user_data.get('high_score', 0) > 0:
                        member = message.guild.get_member(int(user_id))
                        if member:
                            sorted_users.append((member, user_data))
                sorted_users.sort(key=lambda x: x[1]['high_score'], reverse=True)
                top_users = sorted_users[:10]
                embed = discord.Embed(title="🏆 nekoroulette Leaderboard - Top Survivors", description="*Top 10 in dead game*", color=0xffd700)
                medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                if top_users:
                    leaderboard_text = ""
                    for i, (member, user_data) in enumerate(top_users):
                        medal = medals[i] if i < len(medals) else f"{i+1}."
                        high_score = user_data['high_score']
                        total_uses = user_data.get('total_uses', 0)
                        current_streak = user_data.get('current_streak', 0)
                        status = "🔥" if current_streak > 0 else "💀"
                        leaderboard_text += f"{medal} **{member.display_name}** {status}\n"
                        leaderboard_text += f"     └ Record: **{high_score}** | Played: **{total_uses}** | Current: **{current_streak}**\n\n"
                    embed.add_field(name="🎯 Top Survivors", value=leaderboard_text, inline=False)
                else:
                    embed.add_field(name="😅 Chưa có ai chơi", value="Hãy là người đầu tiên thử thách vận may!", inline=False)
                embed.add_field(name="📝 Chú thích", value="🔥 = Đang trong streak | 💀 = Đã chết", inline=False)
                embed.set_footer(text=f"📊 Tổng {len(data)} người đã chơi • Cập nhật lúc {datetime.now().strftime('%H:%M')}", icon_url=bot.user.avatar.url)
                await message.channel.send(embed=embed)
            return
        if last_used and (now - last_used).total_seconds() < COOLDOWN_SECONDS:
            msg = await message.channel.send("<:luom:1391968383393726534> vội thế à")
            await asyncio.sleep(2)
            await msg.delete()
            return
        else:
            user_cooldowns[uid] = now
            bot._user_cooldowns = user_cooldowns
        user_data = data.get(uid, {"total_uses": 0, "last_timeout": None, "current_streak": 0, "high_score": 0})
        if len(args) == 1 and args[0].isdigit():
            choice = int(args[0])
            if not 1 <= choice <= 6:
                await message.channel.send("Chọn số từ 1 đến 6.")
                return

            if user_data["last_timeout"]:

                last_naive = datetime.fromisoformat(user_data["last_timeout"])

                last = pytz.UTC.localize(last_naive)
                
                if now - last < timedelta(hours=2):
                    await message.channel.send("Bạn đang bị timeout.")
                    return
            suspense_msg = await message.channel.send("Bạn khá là....")
            await asyncio.sleep(2)
            bullet = random.randint(1, 6)
            user_data["total_uses"] += 1
            if choice == bullet:
                user_data["last_timeout"] = now.isoformat()
                user_data["current_streak"] = 0
                data[uid] = user_data
                save_json(roulette_file, data)
                try:
                    await message.author.timeout(timedelta(hours=2), reason="Trúng đạn trong nekoroulette 🎯")
                    await suspense_msg.edit(content="Bạn không được may mắn lắm thì phải..... <:HarukaSalute:1398351733767278742> <:HarukaSalute:1398351733767278742>")
                except Exception as e:
                    await suspense_msg.edit(content=f"❌ Không thể timeout: `{e}`")
            else:
                user_data["current_streak"] += 1
                if user_data["current_streak"] > user_data["high_score"]:
                    user_data["high_score"] = user_data["current_streak"]
                data[uid] = user_data
                save_json(roulette_file, data)
                await suspense_msg.edit(content="Bạn khá là may mắn đó <:UmiSip:1398351745779892325>")

    elif content.startswith("nekohelp"):
        embed = discord.Embed(title="<:UmiWink:1401555090396942458> neko Bot - Hướng dẫn sử dụng", description="*Chào mừng bạn đến với thế giới của neko!* <:HarukaSalute:1398351733767278742>", color=0x29a8e0)
        embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
        embed.add_field(name="🎮 **GAME & GIẢI TRÍ**", value="`nekoroll <số>` - Random từ 0 đến số đó\n`nekoroll <x> <y>` - Random từ x đến y\n`nekopick A,B,C` - Chọn ngẫu nhiên từ danh sách", inline=False)
        embed.add_field(name="🎯 **RUSSIAN ROULETTE**", value="`nekoroulette <1-6>` - Chơi súng lục ổ quay \n`nekoroulette rank` - Xem thống kê cá nhân\n`nekoroulette top` - Bảng xếp hạng top 10", inline=False)
        embed.add_field(name="📊 **HỆ THỐNG LEVEL**", value="`nekoexp` - Xem EXP và tiến độ của bạn\n`nekoexp @user` - Xem EXP của người khác", inline=False)
        embed.set_footer(text=f"🌊 Made with 💙 by neko • {len([cmd for cmd in ['nekoroll', 'nekopick', 'nekoroulette', 'nekoexp', 'nekohelp']]) + (2 if message.author.guild_permissions.moderate_members else 0)} commands available", icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        await message.channel.send(embed=embed)

    elif content.startswith("nekomute"):
        if not message.author.guild_permissions.moderate_members:
            await message.channel.send(" nhiễu.")
            return
        args = content.split()
        if len(args) < 3:
            await message.channel.send("")
            return
        try:
            if message.mentions:
                target = message.mentions[0]
            else:
                await message.channel.send("ai thế? ")
                return
            minutes = int(args[2]) if args[2].isdigit() else 10
            reason = " ".join(args[3:]) if len(args) > 3 else "Không có lý do"
            if str(target.id) in ["842942662977781761", "1284520590954463302", "1198110578988818513", "1235666148964434022"]:
                await message.author.timeout(timedelta(minutes=minutes), reason="adu tạo phản <:__:1391968369867096104>")
                await message.channel.send(f"adu tạo phản <:__:1391968369867096104>  ")
                return
            await target.timeout(timedelta(minutes=minutes), reason=reason)
            await message.channel.send(f" <:hmmh:1402863680722571326> Đã nín {target.mention} trong {minutes} phút. Lý do: {reason}")
        except Exception as e:
            await message.channel.send(f"❌ Lỗi khi mute: {e}")

    elif content.startswith("nekolock"):
        # Yêu cầu quyền `manage_channels`
        if not message.author.guild_permissions.manage_channels:
            await message.channel.send("<:job:1404855007169351732>.")
            return

        try:
            # Lấy role @everyone (role mặc định)
            overwrite = message.channel.overwrites_for(message.guild.default_role)
            # Thiết lập quyền gửi tin nhắn thành False
            overwrite.send_messages = False
            
            # Áp dụng quyền mới
            await message.channel.set_permissions(message.guild.default_role, overwrite=overwrite, reason=f"Khóa kênh bởi {message.author.display_name}")
            await message.channel.send(f"Đã khóa")
        
        except discord.Forbidden:
            await message.channel.send("❌ Bot không có đủ quyền để khóa kênh này. Hãy kiểm tra lại quyền hạn của bot.")
        except Exception as e:
            await message.channel.send(f"❌ Lỗi khi khóa kênh: {e}")

    elif content.startswith("nekounlock"):

        if not message.author.guild_permissions.manage_channels:
            await message.channel.send("<:job:1404855007169351732>.")
            return

        try:

            overwrite = message.channel.overwrites_for(message.guild.default_role)

            overwrite.send_messages = None

            await message.channel.set_permissions(
                message.guild.default_role,
                overwrite=overwrite,
                reason=f"Mở khóa kênh bởi {message.author.display_name}"
            )
            await message.channel.send(f"Đã mở khóa.")
        
        except discord.Forbidden:
            await message.channel.send("❌ Bot không có đủ quyền để mở khóa kênh này. Hãy kiểm tra lại quyền hạn của bot.")
        except Exception as e:
            await message.channel.send(f"❌ Lỗi khi mở khóa kênh: {e}")

    elif content.startswith("nekoga"):
        
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

        end_time = datetime.now(pytz.UTC) + timedelta(minutes=duration_minutes)
        end_time_vn = end_time.astimezone(vn_tz) 

        # --- Tạo Embed Giveaway ---
        embed = discord.Embed(
            title=f"<:Hehe:1233447270373134447> GIVEAWAY ",
            description=f"\n\n{prize}\n**WINNER:** {num_winners}\n**END:** {discord.utils.format_dt(end_time, 'R')}",
            color=0x7992da
        )
        embed.set_footer(text=f"Tạo bởi: {message.author.display_name}", icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        
        # Gửi Embed và Reaction
        ga_message = await message.channel.send(embed=embed)
        await ga_message.add_reaction("<:pepeOK:1233449603076984912>")
        
        
        ga_id = str(ga_message.id)
        active_giveaways[ga_id] = {
            "channel_id": message.channel.id,
            "end_time": end_time,
            "prize": prize,
            "winners": num_winners
        }
        
        
        bot.loop.create_task(
            handle_giveaway_end(ga_message, end_time, num_winners, prize)
        )
        try:
            await message.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
    elif content.startswith(("nekoban", "^nekoban")):
        if message.guild is None:
            await message.channel.send("")
            return
        if not message.author.guild_permissions.ban_members:
            await message.channel.send(" lượn")
            return
        if not message.guild.me.guild_permissions.ban_members:
            await message.channel.send("hard.")
            return
        args = content.split()
        if len(args) < 2 and not message.mentions:
            await message.channel.send("")
            return
        target = None
        reason_start = 2
        if message.mentions:
            target = message.mentions[0]
        else:
            if args[1].isdigit():
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
        reason = " ".join(args[reason_start:]).strip() if len(args) > reason_start else ""
        try:
            await target.ban(reason=reason if reason else "No reason")
            await message.channel.send(f"Đã ban {target.mention}")
        except Exception as e:
            await message.channel.send(f"❌ Lỗi khi ban: {e}")
            
    log_message_to_file(message)
    await bot.process_commands(message)
bot_token("") 
    
