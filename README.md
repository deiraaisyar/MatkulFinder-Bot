# MatkulFinder Bot 🤖

An intelligent course recommendation system with a conversational Telegram bot interface. This bot helps computer science students find the best elective courses based on their interests, career goals, completed courses, and current semester.

## Features ✨

- **Smart Course Recommendations**: Multi-factor scoring system considering:
  - Prerequisites and corequisites
  - Student interests
  - Career goals with lab preferences
  - SKS (credit) requirements
  - Semester progression
  - Lab category matching (Algorithms, Software Engineering, AI, Computer Systems)

- **Semester-Aware**: Automatically recommends courses for the next semester based on current semester
  - Supports numeric semesters (1-8)
  - Supports Indonesian semester terms (gasal/genap)

- **Career-Focused**: Maps career goals to relevant lab categories:
  - Frontend/Backend/Full-stack → Software Engineering & Algorithms
  - Data Scientist/ML Engineer → AI & Software Engineering
  - DevOps/System Admin → Computer Systems & Software Engineering
  - And many more career paths

- **Conversational Telegram Interface**: Step-by-step guided conversation to gather all necessary information

## Setup Instructions 🚀

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token you receive

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your bot token:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### 4. Run the Bot

```bash
python telegram/matkulfinder_bot.py
```

You should see:
```
🤖 MatkulFinder Bot is running...
Press Ctrl+C to stop.
```

## Using the Bot 💬

1. Open Telegram and find your bot
2. Send `/start` to begin
3. Follow the conversation:
   - Enter your name
   - List completed courses (e.g., `MII21-1201, MII21-1203`)
   - Enter current semester (e.g., `3`, `gasal`, `genap`)
   - List your interests (e.g., `machine learning, web development`)
   - Enter career goal (e.g., `data scientist`, `frontend developer`)
   - Enter desired SKS (e.g., `2`, `3`)
4. Receive personalized course recommendations!

### Example Conversation

```
User: /start
Bot: Welcome to MatkulFinder Bot! 🎓
     I'm here to help you find the perfect elective courses.
     Let's start! What's your name?

User: Alice
Bot: Nice to meet you, Alice! 😊
     Now, Alice, please list the courses you have already taken...

User: MII21-1201, MII21-1203, MII21-2401
Bot: Got it, Alice! ✅
     What semester are you currently in?

User: 3
Bot: Thanks, Alice! 👍
     What topics are you interested in?

User: machine learning, ai, data science
Bot: Great, Alice! 🎯
     What's your target career?

User: data scientist
Bot: Perfect, Alice! 💼
     How many SKS (credits) would you like to take?

User: 3
Bot: Thank you, Alice! 🚀
     I'm processing your recommendations...
     
Bot: 📚 Course Recommendations for Alice
     
     1. MII21-3401 - Pembelajaran Mesin
        Machine Learning
        SKS: 3 | Score: 85
        Reasons:
        • Interest match: machine learning
        • Career relevant: data scientist
        • Lab preference match: AI lab
```

## Project Structure 📁

```
MatkulFinder-Bot/
├── data/
│   ├── cs_courses.json          # All CS courses data
│   ├── prerequisite_rules.json   # Course prerequisites
│   └── elective_courses.json     # Scraped elective courses
├── model/
│   ├── course_recommender.py     # Recommendation engine
│   └── smart_course_planner.py   # (Optional) Planning utilities
├── telegram/
│   └── matkulfinder_bot.py       # Telegram bot interface
├── web/
│   ├── backend/                  # (Optional) Web API
│   └── frontend/                 # (Optional) Web UI
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Course Recommender API 🔧

You can also use the recommender programmatically:

```python
from model.course_recommender import CourseRecommender

recommender = CourseRecommender()

recommendations = recommender.recommend_courses(
    courses_taken=["MII21-1201", "MII21-1203"],
    interests=["machine learning", "ai"],
    target_career="data scientist",
    sks_preference=3,
    current_semester="3",
    sks_must_match=True,  # Strict SKS filtering
    top_n=5
)

for rec in recommendations:
    print(f"{rec['course']['code']}: {rec['score']}")
```

## Scoring System 📊

The recommender uses a weighted scoring system:

| Factor | Points | Notes |
|--------|--------|-------|
| Prerequisites satisfied | +50 | Must have all prerequisites |
| Corequisites present | +20 | +10 if already taken |
| Interest match | +15 each | Matches course keywords |
| Career relevance | +10 | Matches career keywords |
| SKS match | +5 | Matches desired credit hours |
| Semester match | +15 | Available in target semester |
| Lab preference | +20/+12/+6/+3 | Priority 1/2/3/4 for career |

## Career-Lab Mapping 🎯

The system maps career goals to relevant lab categories:

- **Frontend/Backend/Full-stack Developer** → Software Engineering, Algorithms
- **Data Scientist/ML Engineer** → AI, Software Engineering, Algorithms
- **DevOps/System Admin** → Computer Systems, Software Engineering
- **Mobile Developer** → Software Engineering, Algorithms
- **AI Researcher** → AI, Algorithms
- **Security Specialist** → Computer Systems, Software Engineering
- **And more...**

## Commands 🎮

- `/start` - Start a new recommendation session
- `/cancel` - Cancel the current conversation

## Troubleshooting 🔍

### Bot doesn't respond
- Check that the bot token in `.env` is correct
- Verify the bot is running (check terminal output)
- Make sure you've installed all dependencies

### No recommendations found
- Check if you've met the prerequisites for available courses
- Try adjusting SKS preference (use 3 instead of 2)
- Verify your current semester is correct

### Import errors
- Run `pip install -r requirements.txt` again
- Ensure you're using Python 3.7+

## Contributing 🤝

Feel free to submit issues or pull requests to improve the bot!

## License 📄

This project is for educational purposes.

---

Made with ❤️ for UGM Computer Science students
AI project CSA - Group 2
