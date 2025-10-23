# MatkulFinder Bot 🤖

An intelligent course recommendation and planning bot for CS students. It provides two features: a knowledge-based Course Recommender and an A*-driven Smart Course Planner, accessible via Telegram.

## Features ✨

1) Course Recommender (knowledge-based)
- Ranks elective courses for your next semester using keyword matches and lab preferences from the knowledge base.
- Considers interests, target career, semester offering, and prerequisites.

2) Smart Course Planner (knowledge-based + A*)
- Builds a multi-semester plan choosing exactly one elective per semester.
- Uses knowledge-based scoring to weight edges, then A* to pick the lowest path-cost elective each term.
- Constraints: elective-only, offered-in-semester, prerequisites satisfied.

## Knowledge Base 📚

- `data/cs_courses.json` — Master catalog of courses:
  - Course Code, Name, SKS, Lab Category, Description Keywords, Semesters Offered
- `data/prerequisite_rules.json` — Map of course → prerequisites (with is_corequisite flags)
- `data/career_keywords.json` — Keywords per career for relevance matching
- `data/lab_preferences.json` — Ordered lab preferences per career (e.g., ["ai", "algkom", "rpld", "skj"]) 

## How it works (short) 🧠

- Scoring: interest hits (+15 each), career relevance (+10), lab preference weights (20/12/6/3), etc.
- Planner graph edge cost: lower cost for higher-scoring, relevant courses; A* finds best prerequisite-aware path to each candidate.

## Setup (local) 🚀

1) Install dependencies
```bash
pip install -r requirements.txt
```

2) Create a Telegram bot and token
- Talk to @BotFather → /newbot → copy the token

3) Set environment and run
```bash
echo "TELEGRAM_BOT_TOKEN=<YOUR_TOKEN>" > .env
python telegram/matkulfinder_bot.py
```
You should see:
```
🤖 MatkulFinder Bot is running...
Press Ctrl+C to stop.
```

## Docker (local) �

Build and run (long polling; no ports exposed):
```bash
docker build -t matkulfinder-bot:latest .
docker run -d --name matkulfinder-bot \
  --restart=always \
  -e TELEGRAM_BOT_TOKEN=<YOUR_TOKEN> \
  matkulfinder-bot:latest
```

## Deploy on Google Compute Engine (VM) ☁️

1) Create VM (Ubuntu) and install Docker
```bash
gcloud compute instances create matkul-bot \
  --machine-type=e2-micro \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --zone=asia-southeast2-a

gcloud compute ssh matkul-bot --zone=asia-southeast2-a
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl enable --now docker
```

2) Pull code, build, and run
```bash
git clone https://github.com/<your-user>/MatkulFinder-Bot.git
cd MatkulFinder-Bot
docker build -t matkulfinder-bot:latest .
docker run -d --name matkulfinder-bot \
  --restart=always \
  -e TELEGRAM_BOT_TOKEN=<YOUR_TOKEN> \
  matkulfinder-bot:latest
```

Tip: Ctrl+C in `docker logs -f` only stops viewing logs; the container keeps running. Use `docker stop/start` to manage it.

## Using the Bot �

Flow:
- Choose feature: Course Recommender or Smart Course Planner
- Provide: courses taken, current semester, interests, target career
- Recommender: returns top-N electives with brief reasons
- Planner: returns one elective per semester with code/name/SKS

## Dev utilities 🧪

- Test the planner logic:
```bash
python scripts/test_smart_course_planner.py
```

- A* visualization (optional): open `visualize_astar.ipynb` and run the cells.

## Troubleshooting 🔍

- Invalid token: ensure you passed a real token from @BotFather (not a placeholder). Re-run container with `-e TELEGRAM_BOT_TOKEN=<YOUR_TOKEN>`.
- No candidates in a semester: you may be missing prerequisites or course isn’t offered that term.
- Dependencies: `pip install -r requirements.txt` (Python 3.10+ recommended).

## Project Structure 📁

```
MatkulFinder-Bot/
├── data/
│   ├── cs_courses.json
│   ├── prerequisite_rules.json
│   ├── career_keywords.json
│   └── lab_preferences.json
├── model/
│   ├── course_recommender.py
│   └── smart_course_planner.py
├── scripts/
│   └── test_smart_course_planner.py
├── telegram/
│   └── matkulfinder_bot.py
├── visualize_astar.ipynb
├── Dockerfile
├── requirements.txt
└── README.md
```

## License 📄

For educational purposes.

— Made with ❤️ for UGM CS students
