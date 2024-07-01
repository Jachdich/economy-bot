import asterpy, time, asyncio, json, datetime, re, random, math


client = asterpy.Client("bean", "a")
client.add_server("cospox.com", 2345, uuid=1473552365939855)

users = {}

GREEN = 0x66BB6A
RED   = 0xEF5350
BLUE  = 0x03A9F4

WORK_WAIT_SECONDS = 10 * 60

SLUT_WAIT_SECONDS = 15 * 60
SLUT_MIN_GAIN = 800
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
MIN_BET = 100

PREFIX = "€"
CURRENCY = "€"

responses_pending = {}
lock = asyncio.Condition()

SUITS = ["♣", "♠", "♥", "♦"]
CARDS = {"A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10}
DECK = [card + suit for suit in SUITS for card in CARDS]
deck = DECK.copy()
random.shuffle(deck)

def format_money(amt):
    if amt < 0:
        amt = -amt
        minus = "-"
    else:
        minus = ""

    if amt % 1 == 0.0:
        amt = int(amt)
    else:
        amt = f"{amt:.2f}"
    return f"{minus}{CURRENCY}{amt}"

async def get_response(ctx: asterpy.Message):
    async with lock:
        responses_pending[(ctx.author.uuid, ctx.channel.uuid)] = None
        while responses_pending[(ctx.author.uuid, ctx.channel.uuid)] is None:
            await lock.wait()

    response = responses_pending[(ctx.author.uuid, ctx.channel.uuid)]
    del responses_pending[(ctx.author.uuid, ctx.channel.uuid)]
    return response

def hand_value(hand):
    total = 0
    soft = False
    for card in sorted(hand, key=lambda a: a.startswith("A")):
        if card[0] == "A":
            if total + 11 > 21:
                total += 1
            else:
                total += 11
                if total != 21:
                    soft = True
        else:
            total += CARDS[card[:-1]]

    return total, soft

async def blackjack(ctx: asterpy.Message):
    # TODO doesn't win automatically if you have blackjack
    global deck
    argv = ctx.content.split(" ")
    if len(argv) != 2:
        await ctx.channel.send(f"Wrong arguments! Usage: {argv[0]} <amount or all>")
        return
    if argv[1] == "all":
        amount = users[ctx.author.uuid].cash
    else:
        try:
            amount = float(argv[1])
        except:
            await ctx.channel.send(f"Invalid amount!")
            return

    if amount < MIN_BET:
        await ctx.channel.send(f"You must bet at least {format_money(MIN_BET)}!")
        return

    if amount > users[ctx.author.uuid].cash:
        await ctx.channel.send(f"You can't bet {format_money(amount)} because you only have {format_money(users[ctx.author.uuid].cash)} in cash")
        return
    users[ctx.author.uuid].cash -= amount

    if len(deck) < 16:
        deck = DECK.copy()
        random.shuffle(deck)

    dealer_hand = [deck.pop()]
    dealer_next = deck.pop()
    player_hand = [deck.pop(), deck.pop()]

    def format_value(value):
        total, soft = value
        return ("Soft " if soft else "") + ("Blackjack" if total == 21 else str(total))

    def format_message(header, actions):
        msg = f"""{header}
Your hand:   {' '.join(player_hand)} Value: {format_value(hand_value(player_hand))}
Dealer hand: {' '.join(dealer_hand)} {'🎴' if len(dealer_hand) == 1 else ''} Value: {format_value(hand_value(dealer_hand))}"""
        if len(actions) != 0:
            msg += "\nActions: " + ", ".join(actions)
        msg += f"\nCards remaining: {len(deck)}"
        return msg

    if hand_value(player_hand)[0] > 21:
        info_message = await ctx.channel.send(format_message(f"Blackjack: Blackjack {format_money(amount * 2)}", []))
        users[ctx.author.uuid].cash += amount * 2
        return
    else:
        info_message = await ctx.channel.send(format_message("Blackjack", ["Hit", "Stand"]))
    
    while True:
        action = None
        while not action in ["hit", "stand"]:
            action = (await get_response(ctx)).content

        if action == "hit":
            player_hand.append(deck.pop())
            header = "Blackjack"
            if hand_value(player_hand)[0] > 21:
                await info_message.edit(format_message(f"Blackjack: Bust {format_money(-amount)}", []))
                break

            await info_message.edit(format_message("Blackjack", ["Hit", "Stand"]))

        if action == "stand":
            dealer_hand.append(dealer_next)
            while hand_value(dealer_hand)[0] < 17:
                dealer_hand.append(deck.pop())

            if hand_value(dealer_hand)[0] > 21:
                result = f"Dealer bust {format_money(amount)}"
                users[ctx.author.uuid].cash += amount * 2
            elif hand_value(dealer_hand)[0] < hand_value(player_hand)[0]:
                result = f"Win {format_money(amount)}"
                users[ctx.author.uuid].cash += amount * 2
            elif hand_value(dealer_hand)[0] == hand_value(player_hand)[0]:
                result = "Push (money back)"
                users[ctx.author.uuid].cash += amount
            else:
                result = f"Loss {format_money(-amount)}"
            msg = format_message("Blackjack: " + result, [])
            await info_message.edit(msg)
            break
    

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

    for author_id, channel_id in responses_pending:
        if message.author.uuid == author_id and message.channel.uuid == channel_id:
            responses_pending[(author_id, channel_id)] = message
            async with lock:
                lock.notify()

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
Cash:  {format_money(user.cash)}
Bank:  {format_money(user.bank)}
Total: {format_money(user.bank + user.cash)}"""
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
        await send_success(message, random.choice(MESSAGES["work"]).replace("{amount}", format_money(amount)), emoji=False)

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
                await send_error(message, f"You cannot deposit {format_money(0)}.")
                return
            
            amt = min(MAX_BANK - user.bank, amt)
            if MAX_BANK - user.bank <= 0:
                await send_error(message, "Maximum bank balance reached.")
                return
            msg = f"Deposited {format_money(amt)} to your bank!"
            user.bank += amt
            user.cash -= amt
        elif message.content.startswith(PREFIX + "with"):
            if amt > user.bank:
                await send_error(message, f"You don't have that much money to withdraw. You currently have {format_money(user.bank)} in the bank.")
                return
            msg = f"Withdrew {format_money(amt)} from your bank!"
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
            await send_success(message, random.choice(MESSAGES[action]["good"]).replace("{amount}", format_money(amount)), emoji=False)
        else:
            amount = (user.cash + user.bank) * (random.randint(minpercent, maxpercent) / 100)
            user.cash -= round(amount, 2)
            await send_error(message, random.choice(MESSAGES[action]["bad"]).replace("{amount}", format_money(amount)), emoji=False)

    if message.content.startswith(PREFIX + "bj") or message.content.startswith(PREFIX + "blackjack"):
        await blackjack(message)
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
