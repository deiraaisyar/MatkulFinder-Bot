import json
import sys
from pathlib import Path


def main():
    # Make 'model' importable when running from repo root
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / 'model'))

    try:
        from smart_course_planner import plan_until_graduation_astar
    except Exception as e:
        print(f"Import error: {e}", file=sys.stderr)
        sys.exit(1)

    name = 'Test Simplified Planner with Caps'
    courses_taken = ['MII21-1201','MII21-1203','MII21-2401','MII21-1002']
    interests = ['machine learning','AI']
    career_goal = 'data scientist'
    current_semester = 3

    try:
        plan = plan_until_graduation_astar(
            name=name,
            courses_taken=courses_taken.copy(),
            interests=interests,
            career_goal=career_goal,
            current_semester=current_semester,
            per_semester_sks_cap=6,
            per_semester_count_cap=2,
        )
    except Exception as e:
        print(f"Run error: {e}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps(plan, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
