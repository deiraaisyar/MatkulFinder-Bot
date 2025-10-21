import os
import sys
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# Add parent directory to path to import course_recommender
sys.path.insert(0, str(Path(__file__).parent.parent))
from model.course_recommender import CourseRecommender

# Load environment variables
load_dotenv()

# Conversation states
(
    ASKING_NAME,
    ASKING_COURSES_TAKEN,
    ASKING_CURRENT_SEMESTER,
    ASKING_INTERESTS,
    ASKING_CAREER,
    ASKING_SKS,
) = range(6)

# Initialize recommender
recommender = CourseRecommender(
    courses_path="data/cs_courses.json",
    prereq_path="data/prerequisite_rules.json",
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for the user's name."""
    await update.message.reply_text(
        "👋 Hello! I'm MatkulFinder Bot.\n\n"
        "I will help you find elective courses that match your profile.\n\n"
        "To get started, what's your name?"
    )
    return ASKING_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store name and ask for courses taken."""
    user_name = update.message.text.strip()
    context.user_data["name"] = user_name

    await update.message.reply_text(
        f"Nice to meet you, {user_name}! 😊\n\n"
        f"Now, {user_name}, please list the courses you have already taken "
        f"using their course codes (separated by commas).\n\n"
        f"Example: MII21-1201, MII21-1203, MII21-2401"
    )
    return ASKING_COURSES_TAKEN


async def receive_courses_taken(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parse courses taken and ask current semester."""
    user_name = context.user_data.get("name", "")
    course_codes_text = update.message.text.strip()
    courses_taken = [code.strip().upper() for code in course_codes_text.split(",") if code.strip()]

    context.user_data["courses_taken"] = courses_taken

    await update.message.reply_text(
        f"Got it, {user_name}! ✅\n\n"
        f"What semester are you currently in?\n\n"
        f"Example: 3, 4, gasal, genap"
    )
    return ASKING_CURRENT_SEMESTER


async def receive_current_semester(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parse current semester and ask interests."""
    user_name = context.user_data.get("name", "")
    semester_text = update.message.text.strip().lower()

    # Accept numeric semester or gasal/genap
    context.user_data["current_semester"] = semester_text

    await update.message.reply_text(
        f"Thanks, {user_name}! 👍\n\n"
        f"What topics are you interested in? (separate with commas)\n\n"
        f"Example: machine learning, web development, database"
    )
    return ASKING_INTERESTS


async def receive_interests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parse interests and ask career target."""
    user_name = context.user_data.get("name", "")
    interests_text = update.message.text.strip()
    interests = [interest.strip() for interest in interests_text.split(",") if interest.strip()]

    context.user_data["interests"] = interests

    await update.message.reply_text(
        f"Great, {user_name}! 🎯\n\n"
        f"What's your target career?\n\n"
        f"Example: frontend developer, data scientist, AI engineer"
    )
    return ASKING_CAREER


async def receive_career(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parse career target and ask SKS preference."""
    user_name = context.user_data.get("name", "")
    career = update.message.text.strip()

    context.user_data["target_career"] = career

    await update.message.reply_text(
        f"Perfect, {user_name}! 💼\n\n"
        f"How many SKS (credits) would you like to take?\n\n"
        f"Example: 2, 3, 4"
    )
    return ASKING_SKS


async def receive_sks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store SKS preference, generate recommendations, and end conversation."""
    sks_text = update.message.text.strip()
    sks_list = []
    for s in sks_text.split(","):
        s = s.strip()
        try:
            sks_list.append(int(s))
        except ValueError:
            pass

    context.user_data["sks_preference"] = sks_list if len(sks_list) > 1 else (sks_list[0] if sks_list else None)

    # Get all user data
    name = context.user_data.get("name", "You")
    courses_taken = context.user_data.get("courses_taken", [])
    current_semester = context.user_data.get("current_semester")
    interests = context.user_data.get("interests", [])
    target_career = context.user_data.get("target_career")
    sks_preference = context.user_data.get("sks_preference")

    await update.message.reply_text(
        f"Thank you, {name}! 🚀\n\n"
        f"I'm processing your recommendations...\n"
        f"Please wait a moment!"
    )

    try:
        # Call the recommender
        recommendations = recommender.recommend_courses(
            courses_taken=courses_taken,
            interests=interests,
            target_career=target_career,
            sks_preference=sks_preference,
            current_semester=current_semester,
            sks_must_match=False, 
            top_n=5,
        )

        if not recommendations:
            await update.message.reply_text(
                f"Sorry {name}, no recommendations match your current criteria. 😔\n\n"
                f"Try completing prerequisites or adjusting your preferences.\n\n"
                f"Type /start to try again!"
            )
        else:
            response = f"📚 *Course Recommendations for {name}*\n\n"
            for idx, course in enumerate(recommendations, 1):
                code = course.get("course_code", "N/A")
                name_id = course.get("course_name_id", "N/A")
                name_en = course.get("course_name_en", "N/A")
                sks = course.get("sks", "N/A")
                score = course.get("score", 0)
                reasons = course.get("reason", [])

                response += f"{idx}. *{code}* - {name_id}\n"
                response += f"   _{name_en}_\n"
                response += f"   SKS: {sks} | Score: {score}\n"
                if reasons:
                    response += f"   Reasons:\n"
                    for reason in reasons[:3]:  # Show top 3 reasons
                        response += f"   • {reason}\n"
                response += "\n"

            response += "\nType /start for new recommendations!"

            await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(
            f"Sorry {name}, an error occurred while processing recommendations: {str(e)}\n\n"
            f"Type /start to try again!"
        )

    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "Process cancelled. Type /start to begin again!"
    )
    context.user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """Run the bot (synchronous)."""
    # Get token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not found in .env file!")
        print("Please create a .env file and add: TELEGRAM_BOT_TOKEN=your_token_here")
        sys.exit(1)

    # Create application
    application = Application.builder().token(token).build()

    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            ASKING_COURSES_TAKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_courses_taken)
            ],
            ASKING_CURRENT_SEMESTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_current_semester)
            ],
            ASKING_INTERESTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_interests)
            ],
            ASKING_CAREER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_career)],
            ASKING_SKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sks)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Start the bot
    print("🤖 MatkulFinder Bot is running...")
    print("Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()