import asterpy, time, asyncio, json, datetime, re, random, math


client = asterpy.Client("bean", "a")
client.add_server("cospox.com", 2345, uuid=1508917622722412285)

listening_for_bal = -1

users = {}
goodmsgs = []
badmsgs = []

GREEN = 0x66BB6A
RED   = 0xEF5350
BLUE  = 0x03A9F4

WORK_WAIT_SECONDS = 10 * 60

SLUT_WAIT_SECONDS = 15 * 60
SLUT_MIN = 800
SLUT_MAX = 2200
SLUT_MIN_PERCENT = 35
SLUT_MAX_PERCENT = 75
SLUT_CHANCE = 0.65
SLUT_WAIT_MESSAGE = "You cannot be a slut for"

CRIME_WAIT_SECONDS = 15 * 60
CRIME_MIN_GAIN = 5000
CRIME_MAX_GAIN = 15000
CRIME_MIN_PERCENT_LOSS = 65
CRIME_MAX_PERCENT_LOSS = 90
CRIME_SUCCESS_CHANCE = 0.85
CRIME_WAIT_MESSAGE = "You cannot commit a crime for"
   
MAX_BANK = 10000

def get_bank(): return sum([user.bank for _, user in users.items()])
def get_cash(): return sum([user.cash for _, user in users.items()])
def update_cash(amt):
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
    global users
    global listening_for_bal
    if message.content.startswith("€"):
        if not message.author.uuid in users:
            users[message.author.uuid] = User(message.author.uuid)
    if message.content.startswith("€bal"):
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

        msg = f"""Cash:  £{user.cash}
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
        update_cash(amount)
        await send_success(message, random.choice(goodmsgs).replace("{amount}", str(amount)), emoji=False)

    if message.content.startswith("€dep") or message.content.startswith("€with"):
        if len(message.content.split(" ")) != 2:
            await send_error(message, f"Too few arguments given.\n\nUsage:\n`{message.content.split(' ')[0]} <amount or all>`")
            return

        user = users[message.author.uuid]
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
        user = users[message.author.uuid]
        current_time = datetime.datetime.now().timestamp()
        if message.content == "€slut":
            if current_time - user.last_slut < SLUT_WAIT_SECONDS:
                await send_no_time(message, SLUT_WAIT_MESSAGE, SLUT_WAIT_SECONDS, user.last_slut)
                return

            user.last_slut = current_time

            chance = SLUT_CHANCE
            minamt = SLUT_MIN
            maxamt = SLUT_MAX
            minpercent = SLUT_MIN_PERCENT
            maxpercent = SLUT_MAX_PERCENT
            
        else:
            if current_time - user.last_crime < CRIME_WAIT_SECONDS:
                await send_no_time(message, CRIME_WAIT_MESSAGE, CRIME_WAIT_SECONDS, user.last_crime)
                return

            user.last_crime = current_time
            
        if random.random() > CRIME_SUCCESS_CHANCE:
            amount = random.randint(CRIME_MIN_GAIN, CRIME_MAX_GAIN)
            update_cash(amount)
            await send_success(message, random.choice(goodmsgs).replace("{amount}", str(amount)), emoji=False)
        else:
            amount = (get_cash() + get_bank()) * (random.randint(CRIME_MIN_PERCENT_LOSS, CRIME_MAX_PERCENT_LOSS) / 100)
            update_cash(-round(amount))
            await send_error(message, random.choice(badmsgs).replace("{amount}", str(amount)), emoji=False)

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
