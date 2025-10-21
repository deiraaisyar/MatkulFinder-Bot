# Quick Start Guide 🚀

Follow these simple steps to get your MatkulFinder Bot up and running!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Get Your Bot Token

1. Open Telegram
2. Search for **@BotFather**
3. Send `/newbot`
4. Choose a name for your bot (e.g., "MatkulFinder Helper")
5. Choose a username (e.g., "matkulfinder_ugm_bot")
6. **Copy the token** that BotFather sends you

## Step 3: Configure Your Bot

Create a `.env` file:

```bash
cp .env.example .env
```

Edit the `.env` file and paste your token:

```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

## Step 4: Run the Bot

```bash
python telegram/matkulfinder_bot.py
```

You should see:
```
🤖 MatkulFinder Bot is running...
Press Ctrl+C to stop.
```

## Step 5: Test It!

1. Open Telegram
2. Find your bot (search for the username you created)
3. Send `/start`
4. Follow the conversation!

## Example Test Case

```
/start
→ Name: Alice
→ Courses: MII21-1201, MII21-1203
→ Semester: 3
→ Interests: machine learning, ai
→ Career: data scientist
→ SKS: 3
→ Get recommendations! 🎓
```

## Troubleshooting

### "ERROR: TELEGRAM_BOT_TOKEN not found"
- Make sure you created the `.env` file
- Check that the token is on a line like: `TELEGRAM_BOT_TOKEN=your_token`
- No spaces around the `=` sign

### "ModuleNotFoundError"
- Run: `pip install -r requirements.txt`
- Make sure you're in the project directory

### Bot doesn't respond in Telegram
- Check the terminal - is the bot running?
- Verify the token is correct in `.env`
- Try stopping (Ctrl+C) and restarting the bot

## Need Help?

Check the full [README.md](README.md) for detailed documentation!

---

**Ready to find the perfect courses! 🎓✨**
