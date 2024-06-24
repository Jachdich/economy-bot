import asterpy, time, asyncio, json, datetime, re, random, math


client = asterpy.Client("bean", "a")
client.add_server("cospox.com", 2345, uuid=1508917622722412285)

listening_for_bal = -1

users = {}

GREEN = 0x66BB6A
RED   = 0xEF5350
BLUE  = 0x03A9F4

WORK_WAIT_SECONDS = 10 * 60

SLUT_WAIT_SECONDS = 15 * 60
SLUT_MIN_GAIN = 800000
SLUT_MAX_GAIN = 2200
SLUT_MIN_PERCENT_LOSS = 35
SLUT_MAX_PERCENT_LOSS = 75
SLUT_SUCCESS_CHANCE = 0.65
SLUT_WAIT_MESSAGE = "You cannot be a slut for"

CRIME_WAIT_SECONDS = 15 * 60
CRIME_MIN_GAIN = 5000
CRIME_MAX_GAIN = 15000
CRIME_MIN_PERCENT_LOSS = 65
CRIME_MAX_PERCENT_LOSS = 90
CRIME_SUCCESS_CHANCE = 0.85
CRIME_WAIT_MESSAGE = "You cannot commit a crime for"
   
MAX_BANK = 10000

PREFIX = "€"
CURRENCY = "€"

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

with open("users.json", "r") as f:
    data = f.read()
    print(json.loads(data)["users"].items())
    for key, val in json.loads(data)["users"].items():
        users[int(key)] = User.from_json(val)

with open("messages.json", "r") as f:
    MESSAGES = json.load(f)

def save():
    global users
    data = {"users": {}}
    for uuid, user in users.items():
        data["users"][uuid] = user.to_json()

    with open("users.json", "w") as f:
        f.write(json.dumps(data))


async def send_error(ctx, msg, emoji=True):
    await ctx.channel.send(f"{'⛔ ' if emoji else ''}{msg}")
async def send_success(ctx, msg, emoji=True):
    await ctx.channel.send(f"{'✅ ' if emoji else ''}{msg}")

async def send_no_time(ctx, msg, min_time, last_time):
    to_go = min_time - (datetime.datetime.now().timestamp() - last_time)
    minutes = math.floor(to_go // 60)
    seconds = math.floor(to_go % 60)
    if minutes > 0:
        minutes_string = f"{minutes} minutes and "
    else:
        minutes_string = ""

    await ctx.channel.send(f"⏱ {msg} {minutes_string}{seconds} seconds")

@client.event
async def on_message(message: asterpy.Message):
    if message.author.uuid == client.uuid:
        return
    print(message.content)
    global users
    global listening_for_bal
    if message.content.startswith(PREFIX):
        if not message.author.uuid in users:
            users[message.author.uuid] = User(message.author.uuid)
    if message.content.startswith(PREFIX + "bal"):
        sp = message.content.split(" ")
        if len(sp) == 1:
            user = users[message.author.uuid]
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

        msg = f"""Bank Statement
Cash:  £{user.cash}
Bank:  £{user.bank}
Total: £{user.bank + user.cash}"""
        await message.channel.send(msg)

    if message.content == "€work":
        user = users[message.author.uuid]
        current_time = datetime.datetime.now().timestamp()
        if current_time - user.last_work < WORK_WAIT_SECONDS:
            await send_no_time(message, "You cannot work for", WORK_WAIT_SECONDS, user.last_work)
            return

        user.last_work = current_time
        amount = random.randint(400, 1200)
        user.cash += amount
        await send_success(message, random.choice(MESSAGES["work"]).replace("{amount}", CURRENCY + str(amount)), emoji=False)

    if message.content.startswith(PREFIX + "dep") or message.content.startswith(PREFIX + "with"):
        if len(message.content.split(" ")) != 2:
            await send_error(message, f"Too few arguments given.\n\nUsage:\n`{message.content.split(' ')[0]} <amount or all>`")
            return

        user = users[message.author.uuid]
        amt = message.content.split(" ")[1]
        if amt == "all":
            if message.content.startswith(PREFIX + "with"):
                amt = user.bank
            else:
                amt = user.cash
        elif amt.isdigit():
            amt = int(amt)
        else:
            await send_error(message, f"Invalaid `<amount or all>` argument given.\n\nUsage:\n`{message.content.split(' ')[0]} <amount or all>`")
            return

        if message.content.startswith(PREFIX + "dep"):
            if amt > user.cash:
                await send_error(message, "You don't have that much money to deposit. You currently have £{user.cash} on hand.")
                return
            if amt <= 0:
                await send_error(message, f"You cannot deposit {CURRENCY}0.")
                return
            
            amt = min(MAX_BANK - user.bank, amt)
            if MAX_BANK - user.bank <= 0:
                await send_error(message, "Maximum bank balance reached.")
                return
            msg = f"Deposited {CURRENCY}{amt} to your bank!"
            user.bank += amt
            user.cash -= amt
        elif message.content.startswith(PREFIX + "with"):
            if amt > user.bank:
                await send_error(message, f"You don't have that much money to withdraw. You currently have {CURRENCY}{user.bank} in the bank.")
                return
            msg = f"Withdrew {CURRENCY}{amt} from your bank!"
            user.bank -= amt
            user.cash += amt
        else:
            await message.channel.send(f"You should never see this message lol. info: neither {PREFIX}dep or {PREFIX}with inside of the block that should check for it")
            return
        
        await send_success(message, msg)

    if message.content == PREFIX + "slut" or message.content == PREFIX + "crime":
        user = users[message.author.uuid]
        current_time = datetime.datetime.now().timestamp()
        action = message.content.replace(PREFIX, "")
        if action == "slut":
            if current_time - user.last_slut < SLUT_WAIT_SECONDS:
                await send_no_time(message, SLUT_WAIT_MESSAGE, SLUT_WAIT_SECONDS, user.last_slut)
                return

            user.last_slut = current_time

            chance = SLUT_SUCCESS_CHANCE
            minamt = SLUT_MIN_GAIN
            maxamt = SLUT_MAX_GAIN
            minpercent = SLUT_MIN_PERCENT_LOSS
            maxpercent = SLUT_MAX_PERCENT_LOSS
            
        else:
            if current_time - user.last_crime < CRIME_WAIT_SECONDS:
                await send_no_time(message, CRIME_WAIT_MESSAGE, CRIME_WAIT_SECONDS, user.last_crime)
                return

            user.last_crime = current_time

            chance = CRIME_SUCCESS_CHANCE
            minamt = CRIME_MIN_GAIN
            maxamt = CRIME_MAX_GAIN
            minpercent = CRIME_MIN_PERCENT_LOSS
            maxpercent = CRIME_MAX_PERCENT_LOSS
            
            
        if random.random() > chance:
            amount = random.randint(minamt, maxamt)
            user.cash += amount
            await send_success(message, random.choice(MESSAGES[action]["good"]).replace("{amount}", CURRENCY + str(amount)), emoji=False)
        else:
            amount = (user.cash + user.bank) * (random.randint(minpercent, maxpercent) / 100)
            user.cash -= round(amount)
            await send_error(message, random.choice(MESSAGES[action]["bad"]).replace("{amount}", CURRENCY + str(amount)), emoji=False)

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

client.run()

save()
