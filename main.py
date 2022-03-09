import discord, time, asyncio, json, datetime, re, random, math

intents = discord.Intents.default()
intents.members = True
intents.messages = True

with open("token.txt", "r") as f:
    TOKEN = f.read()

client = discord.Client(intents=intents)

listening_for_bal = -1

users = {}
goodmsgs = []
badmsgs = []

GREEN = 6732650
RED = 15684432
BLUE = 240116

WORK_TIME = 10 * 60

SLUT_TIME = 15 * 60
SLUT_MIN = 800
SLUT_MAX = 2200
SLUT_MIN_PERCENT = 35
SLUT_MAX_PERCENT = 75
SLUT_CHANCE = 0.65
SLUT_MESSAGE = "You cannot be a slut for"

CRIME_TIME = 15 * 60
CRIME_MIN = 5000
CRIME_MAX = 15000
CRIME_MIN_PERCENT = 65
CRIME_MAX_PERCENT = 90
CRIME_CHANCE = 0.85
CRIME_MESSAGE = "You cannot commit a crime for"

MAX_BANK = 10000

def getBank(): return sum([user.bank for _, user in users.items()])
def getCash(): return sum([user.cash for _, user in users.items()])
def updateCash(amt):
    num_users = len(users)
    for _, user in users.items():
        user.cash += round(amt / num_users, 2)

class User:
    def __init__(self, uuid):
        self.cash = 0
        self.bank = 0
        self.uuid = uuid
        self.last_work = 0
        self.last_slut = 0
        self.last_crime = 0
        self.last_income = 0
        self.last_rob = 0

    def from_json(json):
        user = User(json["uuid"])
        user.bank = json.get("bank", 0)
        user.cash = json.get("cash", 0)
        user.last_work = json.get("last_work", 0)
        user.last_slut = json.get("last_slut", 0)
        user.last_crime = json.get("last_crime", 0)
        user.last_income = json.get("last_income", 0)
        user.last_rob = json.get("last_rob", 0)
        return user

    def to_json(self):
        return {"cash": self.cash, "bank": self.bank, "uuid": self.uuid,
                "last_work": self.last_work, "last_slut": self.last_slut, "last_crime": self.last_crime,
                "last_income": self.last_income, "last_rob": self.last_rob}

with open("good.txt", "r") as f: goodmsgs = [i for i in f.read().split("\n") if i != ""]
with open("bad.txt", "r")  as f: badmsgs  = [i for i in f.read().split("\n") if i != ""]

with open("users.json", "r") as f:
    data = f.read()
    print(data)
    print(json.loads(data)["users"].items())
    for key, val in json.loads(data)["users"].items():
        users[int(key)] = User.from_json(val)
    print(users)

def save():
    global users
    data = {"users": {}}
    for uuid, user in users.items():
        data["users"][uuid] = user.to_json()

    with open("users.json", "w") as f:
        f.write(json.dumps(data))


async def send_generic_embed(ctx, msg, colour):
    embed = {
        'author': {
             "name": str(ctx.author),
             "icon_url": str(ctx.author.avatar_url_as(format="png", static_format="png", size=128)),
        },
        'color': colour,
        'type': 'rich',
        'description': msg
    }
    await ctx.channel.send(embed=discord.Embed.from_dict(embed))

async def send_error(ctx, msg, emoji=True):   await send_generic_embed(ctx, f"{':no_entry: ' if emoji else ''}{msg}", RED)
async def send_success(ctx, msg, emoji=True): await send_generic_embed(ctx, f"{':white_check_mark: ' if emoji else ''}{msg}", GREEN)

async def send_no_time(ctx, msg, min_time, last_time):
    to_go = min_time - (datetime.datetime.now().timestamp() - last_time)
    minutes = math.floor(to_go // 60)
    seconds = math.floor(to_go % 60)
    if minutes > 0:
        minutes_string = f"{minutes} minutes and "
    else:
        minutes_string = ""

    await send_generic_embed(ctx, f":stopwatch: {msg} {minutes_string}{seconds} seconds", BLUE)

@client.event
async def on_message(message):
    global users
    global listening_for_bal
    if message.content.startswith("€"):
        if not message.author.id in users:
            users[message.author.id] = User(message.author.id)
    if message.content.startswith("€bal"):
        sp = message.content.split(" ")
        if len(sp) == 1:
            user = users[message.author.id]
        elif len(sp) == 2:
            try:
                uuid = int(sp[1].replace("<", "").replace(">", "").replace("@", "").replace("!", ""))
            except ValueError:
                await send_error(message, f"Invalaid `[user]` argument given.\n\nUsage:\n`€bal [user]`")
                return
            user = users[uuid]
        else:
            await send_error(message, f"Invalaid `[user]` argument given.\n\nUsage:\n`€bal [user]`")
            return
            
        embed = {
            "author": 
                {"name": str(message.author),
                 #"url": "https://unbelievaboat.com/leaderboard/757217204310769695/336829417231745025", TODO
                 "icon_url": str(message.author.avatar_url_as(format="png", static_format="png", size=128)),
                #TODO proxy_url?
            },
            "fields": [
                {"name": "Cash:", "value": f"£{user.cash}", "inline": True},
                {"name": "Bank:", "value": f"£{user.bank}", "inline": True},
                {"name": "Total:", "value": f"£{user.bank + user.cash}", "inline": True}
            ],
            "color": BLUE,
            "timestamp": str(datetime.datetime.utcnow()),
            "type": "rich",
            "description": "Leaderboard Rank: NaNsth"}
        await message.channel.send(embed=discord.Embed.from_dict(embed))

    if message.content == "€transfer":
        listening_for_bal = message.author.id
        await message.channel.send("Okay, now run £bal")

    if message.content == "€work":
        user = users[message.author.id]
        current_time = datetime.datetime.now().timestamp()
        if current_time - user.last_work < WORK_TIME:
            await send_no_time(message, "You cannot work for", WORK_TIME, user.last_work)
            return

        user.last_work = current_time
        amount = random.randint(400, 1200)
        updateCash(amount)
        await send_success(message, random.choice(goodmsgs).replace("{amount}", str(amount)), emoji=False)

    if message.content.startswith("€dep") or message.content.startswith("€with"):
        if len(message.content.split(" ")) != 2:
            await send_error(message, f"Too few arguments given.\n\nUsage:\n`{message.content.split(' ')[0]} <amount or all>`")
            return

        user = users[message.author.id]
        amt = message.content.split(" ")[1]
        if amt == "all":
            if message.content.startswith("€with"):
                amt = user.bank
            else:
                amt = user.cash
        elif amt.isdigit():
            amt = int(amt)
        else:
            await send_error(message, f"Invalaid `<amount or all>` argument given.\n\nUsage:\n`{message.content.split(' ')[0]} <amount or all>`")
            return

        if message.content.startswith("€dep"):
            if amt > user.cash:
                await send_error(message, "You don't have that much money to deposit. You currently have £{user.cash} on hand.")
                return
            if amt <= 0:
                await send_error(message, "You cannot deposit £0.")
                return
            
            amt = min(MAX_BANK - user.bank, amt)
            if MAX_BANK - user.bank <= 0:
                await send_error(message, "Maximum bank balance reached.")
                return
            msg = f"Deposited £{amt} to your bank!"
            user.bank += amt
            user.cash -= amt
        elif message.content.startswith("€with"):
            if amt > user.bank:
                await send_error(message, "You don't have that much money to withdraw. You currently have £{user.bank} in the bank.")
                return
            msg = f"Withdrew £{amt} from your bank!"
            user.bank -= amt
            user.cash += amt
        else:
            await message.channel.send("You should never see this message lol. info: neither €dep or €with inside of the block that should check for it")
            return
        
        await send_success(message, msg)

    if message.content == "€slut" or message.content == "€crime":
        user = users[message.author.id]
        current_time = datetime.datetime.now().timestamp()
        if message.content == "€slut":
            if current_time - user.last_slut < SLUT_TIME:
                await send_no_time(message, SLUT_MESSAGE, SLUT_TIME, user.last_slut)
                return

            user.last_slut = current_time

            chance = SLUT_CHANCE
            minamt = SLUT_MIN
            maxamt = SLUT_MAX
            minpercent = SLUT_MIN_PERCENT
            maxpercent = SLUT_MAX_PERCENT
            
        else:
            if current_time - user.last_crime < CRIME_TIME:
                await send_no_time(message, CRIME_MESSAGE, CRIME_TIME, user.last_crime)
                return

            user.last_crime = current_time
            chance = CRIME_CHANCE
            minamt = CRIME_MIN
            maxamt = CRIME_MAX
            minpercent = CRIME_MIN_PERCENT
            maxpercent = CRIME_MAX_PERCENT
            
        if random.random() > chance:
            amount = random.randint(minamt, maxamt)
            updateCash(amount)
            await send_success(message, random.choice(goodmsgs).replace("{amount}", str(amount)), emoji=False)
        else:
            amount = (getCash() + getBank()) * (random.randint(minpercent, maxpercent) / 100)
            updateCash(-round(amount))
            await send_error(message, random.choice(badmsgs).replace("{amount}", str(amount)), emoji=False)

    if listening_for_bal != -1 and message.author.id == 292953664492929025 and len(message.embeds) > 0:
        embed = message.embeds[0].to_dict()
        if embed["author"]["name"] == str(client.get_user(listening_for_bal)):
            user = users[listening_for_bal]
            user.cash = int(embed["fields"][0]["value"].replace("£", "").replace(",", ""))
            user.bank = int(embed["fields"][1]["value"].replace("£", "").replace(",", ""))
            listening_for_bal = -1
    save()         
@client.event
async def on_ready():
    print("ready lol")
    # chan = client.get_channel(790920768951025674)
    # good = []
    # bad = []
    # async for message in chan.history(limit=20000000):
        # if message.author.id == 292953664492929025 and len(message.embeds) > 0:
            # d = message.embeds[0].to_dict()
            # print(d)
            # if "Reply #" in d.get('footer', {}).get("text", ""):
                # desc = re.sub(r"£[0-9,]+", "£{amount}", d["description"])
                # if d["color"] == GREEN:
                    # good.append(desc)
                    # print("good:", desc)
                # else:
                    # bad.append(desc)
                    # print("bad:", desc)
# 
    # print("\n\n\n")
    # print("\n".join(good))
    # print("\n\n\n")
    # print("\n".join(bad))
# 
    # print("done")

client.run(TOKEN)

save()
