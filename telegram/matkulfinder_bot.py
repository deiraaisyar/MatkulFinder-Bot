import os
import sys
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (Application, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters,)
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))
from model.course_recommender import recommend as kb_recommend
from model.smart_course_planner import plan_until_graduation_astar as plan_astar

(
    ASKING_NAME,
    ASKING_FEATURE,
    ASKING_COURSES_TAKEN,
    ASKING_CURRENT_SEMESTER,
    ASKING_INTERESTS,
    ASKING_CAREER,
    ASKING_SKS,
) = range(7)

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

    keyboard = [["Course Recommender"], ["Smart Course Planner"]]
    await update.message.reply_text(
        f"Nice to meet you, {user_name}! 😊\n\n"
        f"What would you like to use?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASKING_FEATURE

async def receive_feature_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store feature choice and ask for courses taken."""
    choice = (update.message.text or "").strip().lower()
    if "planner" in choice:
        context.user_data["feature"] = "planner"
    else:
        # default to recommender for unknown input
        context.user_data["feature"] = "recommender"

    user_name = context.user_data.get("name", "")
    await update.message.reply_text(
        f"Great! Now, {user_name}, please list the courses you have already taken "
        f"using their course codes (separated by commas).\n\n"
        f"Example: MII21-1201, MII21-1203, MII21-2401",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASKING_COURSES_TAKEN

async def receive_which_features(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask which features to consider for recommendations."""
    user_name = context.user_data.get("name", "")
    await update.message.reply_text(
        f"We have two features to help tailor your recommendations.\n\n"
        f"1. Course Recommender: Help you find elective courses that match your interests and career goals in your next semester.\n"
        f"2. Smart Course Planner: Plan your elective courses over multiple semesters to graduate on time while aligning with your interests and career goals.\n\n"
        f"Thanks, {user_name}! 🙌\n\n"
        f"Which features would you like me to consider for your course recommendations?\n"
        f"Please choose from: interests, target career, SKS preference.\n\n"
        f"Example: interests, target career"
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
        f"What semester are you currently in? (number only)\n\n"
        f"Example: 3, 4"
    )
    return ASKING_CURRENT_SEMESTER

async def receive_current_semester(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parse current semester (numeric only) and ask interests."""
    user_name = context.user_data.get("name", "")
    semester_text = update.message.text.strip()

    # Validate numeric semester 1-8
    try:
        semester_num = int(semester_text)
        if semester_num < 1 or semester_num > 8:
            await update.message.reply_text(
                "Please enter a valid semester number between 1 and 8. Example: 3"
            )
            return ASKING_CURRENT_SEMESTER
    except ValueError:
        await update.message.reply_text(
            "Please enter a number for the semester. Example: 3"
        )
        return ASKING_CURRENT_SEMESTER

    context.user_data["current_semester"] = semester_num

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
    # Branch based on chosen feature
    if context.user_data.get("feature") == "planner":
        # Directly run planner now (one course per semester; no caps needed)
        name = context.user_data.get("name", "You")
        courses_taken = context.user_data.get("courses_taken", [])
        current_semester = context.user_data.get("current_semester")
        interests = context.user_data.get("interests", [])
        target_career = context.user_data.get("target_career")

        await update.message.reply_text(
            f"Perfect, {user_name}! 💼\n\n"
            f"I'm generating your smart multi-semester elective plan (A* picks one best elective per semester, offered that term, prereqs satisfied)..."
        )

        try:
            plan = plan_astar(
                name=name,
                courses_taken=courses_taken,
                interests=interests,
                career_goal=target_career,
                current_semester=current_semester,
                per_semester_sks_cap=None,
                per_semester_count_cap=None,
            )

            schedule = plan.get("schedule", [])
            if not schedule:
                await update.message.reply_text(
                    f"Sorry {name}, I couldn't create a plan with the given info. 😔\n\n"
                    f"Try completing more prerequisites.\n\n"
                    f"Type /start to try again!"
                )
            else:
                lines = [
                    f"📅 Smart Course Plan for {name}",
                    f"• Current semester: {current_semester}",
                    f"• Interests: {', '.join(interests) if interests else '-'}",
                    f"• Target career: {target_career or '-'}",
                    "• Method: A* path-cost selection (1 elective/semester)",
                    "• Constraints: elective-only, offered-in-semester, prerequisites satisfied",
                    ""
                ]
                for term in schedule:
                    sem = term.get("semester")
                    courses = term.get("courses", [])
                    sks = term.get("sks", 0)
                    course_list = []
                    for c in courses:
                        code = c.get("course_code", "N/A")
                        title = c.get("course_name_en", "")
                        try:
                            c_sks = int(c.get("sks") or 0)
                        except Exception:
                            c_sks = 0
                        course_list.append(f"{code} ({c_sks}) - {title}")
                    if course_list:
                        lines.append(f"Semester {sem}:\n- " + "\n- ".join(course_list) + f"\n(SKS: {sks})\n")
                    else:
                        lines.append(f"Semester {sem}: [No electives scheduled]\n(SKS: {sks})\n")

                lines.append("Tip: If some semesters are empty, consider taking missing prerequisites earlier.")
                lines.append("\nType /start to plan again or get recommendations!")
                await update.message.reply_text("\n".join(lines))

        except Exception as e:
            await update.message.reply_text(
                f"Sorry {name}, an error occurred while planning: {str(e)}\n\n"
                f"Type /start to try again!"
            )

        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"Perfect, {user_name}! 💼\n\n"
            f"How many SKS (credits) would you like to take?\n\n"
            f"Example: 2, 3, 4"
        )
        return ASKING_SKS

## receive_planner_caps removed; planner runs immediately after career is provided

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
        # Call the functional recommender (copy version)
        recommendations = kb_recommend(
            taken=courses_taken,
            interests=interests,
            career=target_career,
            top_n=3,
            sks_preference=sks_preference,
            sks_must_match=False,
            semester_preference=None,
            current_semester=current_semester,
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
                name_en = course.get("course_name_en", "N/A")
                score = course.get("score", 0)
                reasons = course.get("reasons", [])

                response += f"{idx}. *{code}*\n"
                response += f"   _{name_en}_\n"
                response += f"   Score: {score}\n"
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
    """Run the bot."""
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
            ASKING_FEATURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_feature_choice)],
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

    print("🤖 MatkulFinder Bot is running...")
    print("Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()