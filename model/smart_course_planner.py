import json
import heapq
from typing import Any, Dict, List, Optional, Tuple

def load_json(path):
    """Load a JSON file from the given path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_knowledge() -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, List[str]], Dict[str, List[str]]]:
    """Load all required data files for courses, prerequisites, and preferences."""
    courses = load_json("data/cs_courses.json") or load_json("data/courses.json")
    prereqs = load_json("data/prerequisite_rules.json") or load_json("data/prerequisites.json")
    career_keywords = load_json("data/career_keywords.json")
    lab_preferences = load_json("data/lab_preferences.json")
    return courses, prereqs, career_keywords, lab_preferences

def is_elective(course):
    """Check if a course is elective based on its 'type' field."""
    return "wajib" not in (course.get("type") or "").lower()

def offered_in_semester(course, sem):
    """Check if a course is offered in a specific semester."""
    sems = course.get("semesters") or []
    if not sems:
        return True
    return sem in [int(s) for s in sems if isinstance(s, (int, str)) and str(s).isdigit()]

def prereq_ok(code, taken, rules):
    """Return True if all prerequisites for a given course are already taken."""
    entry = rules.get(code)
    if not entry:
        return True
    prereqs = [p.get("code") for p in entry.get("prerequisites", []) if not p.get("is_corequisite")]
    return set(prereqs).issubset(taken)

def matches_interest(course, interests):
    """Count how many user interests appear in the course name or topics."""
    text = " ".join([
        course.get("course_name_en", ""),
        course.get("course_name_id", ""),
        " ".join(course.get("topics", []) or []),
    ]).lower()
    return sum(1 for i in interests if i.lower() in text)

def is_relevant_to_career(course, target, career_keywords):
    """Check if a course is relevant to the target career using keyword matching."""
    target = (target or "").lower()
    haystack = " ".join([
        course.get("course_name_en", ""),
        course.get("course_name_id", ""),
        " ".join(course.get("topics", []) or []),
        course.get("type", "") or "",
    ]).lower()
    for career, keywords in (career_keywords or {}).items():
        ck = (career or "").lower()
        if ck in target or target in ck:
            if any((kw or "").lower() in haystack for kw in (keywords or [])):
                return True
    for token in target.split():
        if token and token in haystack:
            return True
    return False

def lab_category(course_type):
    """Classify course type into a lab category for weighting purposes."""
    t = (course_type or "").lower()
    if "algoritma" in t or "komputasi" in t:
        return "algkom"
    if "rekayasa perangkat lunak" in t or "rpl" in t or "data" in t:
        return "rpld"
    if "sistem cerdas" in t or "intelligent" in t:
        return "ai"
    if "jaringan" in t or "network" in t:
        return "skj"
    return None

def lab_preferences_for_career(career_goal, lab_preferences):
    """Find the preferred lab categories for a specific career goal."""
    ck = (career_goal or "").lower()
    for k, v in (lab_preferences or {}).items():
        lk = (k or "").lower()
        if lk in ck or ck in lk:
            return v or []
    return []

def score_course(course, interests, career_goal, career_keywords, lab_preferences):
    """Compute a course score based on interests, career goal, and lab preference."""
    score = 0
    score += 15 * matches_interest(course, interests or [])
    if career_goal and is_relevant_to_career(course, career_goal, career_keywords):
        score += 10
    lab_cat = lab_category(course.get("type"))
    lab_pref = lab_preferences_for_career(career_goal, lab_preferences)
    if lab_cat and lab_pref and lab_cat in lab_pref:
        idx = lab_pref.index(lab_cat)
        weights = [20, 12, 6, 3]
        score += weights[idx] if idx < len(weights) else 2
    return score

def prereq_depth(prereq_rules, code, depth=0):
    """Recursively compute the prerequisite depth for a given course."""
    entry = prereq_rules.get(code)
    if not entry:
        return depth
    prereqs = [p.get("code") for p in entry.get("prerequisites", []) if p.get("code")]
    if not prereqs:
        return depth
    return max(prereq_depth(prereq_rules, p, depth + 1) for p in prereqs)

def build_course_graph(courses, prereq_rules, interests, career_goal, career_keywords, lab_preferences):
    """
    Build a directed graph of courses.
    Each edge weight (cost) depends on prerequisite depth and course score.
    Lower cost means the course is more favorable.
    """
    graph = {}
    course_map = {c.get("course_code"): c for c in courses if c.get("course_code")}
    for code, course in course_map.items():
        graph.setdefault(code, [])
        entry = prereq_rules.get(code, {})
        prereqs = [p.get("code") for p in entry.get("prerequisites", []) if p.get("code")]
        for pre in prereqs:
            if pre not in course_map:
                continue
            sc = score_course(course, interests, career_goal, career_keywords, lab_preferences)
            depth = prereq_depth(prereq_rules, code)
            # Reduce the impact of depth so high-relevance courses (e.g., AI lab) are not dominated by zero-prereq courses
            cost = (1.0 + 0.2 * depth) / (sc + 1e-5)
            graph.setdefault(pre, []).append((code, cost))
    return graph

def heuristic(a, b, prereq_rules):
    """Estimate the distance between two courses using prerequisite depth difference."""
    return abs(prereq_depth(prereq_rules, a) - prereq_depth(prereq_rules, b))

def astar(graph, start, goal, prereq_rules):
    """Perform A* search on the course graph to find the optimal prerequisite path."""
    open_set = [(0, start)]
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal, prereq_rules)}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            # Reconstruct path from start to goal
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            return list(reversed(path))

        for neighbor, cost in graph.get(current, []):
            tentative_g = g_score[current] + cost
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal, prereq_rules)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return None

def path_cost(graph: Dict[str, List[Tuple[str, float]]], path: List[str]) -> float:
    """Compute total path cost based on edge weights in the graph."""
    total = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i+1]
        for nb, cost in graph.get(u, []):
            if nb == v:
                total += cost
                break
    return total

def plan_until_graduation_astar(
    name: str,
    courses_taken: List[str],
    interests: List[str],
    career_goal: str,
    current_semester: int,
    per_semester_sks_cap: Optional[int] = None,
    per_semester_count_cap: Optional[int] = 5,
):
    """
    Plan courses until graduation using A* to choose the next best course each semester.
    One course per semester is chosen for simplicity.
    """
    courses, prereq, career_keywords, lab_preferences = load_knowledge()
    graph = build_course_graph(courses, prereq, interests, career_goal, career_keywords, lab_preferences)
    course_map = {c.get("course_code"): c for c in courses if c.get("course_code")}

    available_nodes = [c.get("course_code") for c in courses if c.get("course_code")]
    taken = set(courses_taken)
    schedule = []

    for sem in range(current_semester + 1, 8):
        chosen = []
        total_sks = 0

        # Candidate courses that satisfy prerequisites and are offered this semester
        candidates = [
            c for c in available_nodes
            if prereq_ok(c, taken, prereq)
            and c not in taken
            and is_elective(course_map.get(c, {}))
            and offered_in_semester(course_map.get(c, {}), sem)
        ]

        best_item = None  # (total_cost, -score, code, course)
        for code in candidates:
            course = course_map.get(code)
            if not course:
                continue

            # Use direct prerequisites as starting nodes for A*
            entry = prereq.get(code, {})
            pre_list = [p.get("code") for p in entry.get("prerequisites", []) if p.get("code")]
            start_nodes = pre_list if pre_list else [code]

            # Compute a baseline "own" cost using the same formula as edges
            sc = score_course(course, interests, career_goal, career_keywords, lab_preferences)
            depth = prereq_depth(prereq, code)
            own_cost = (1.0 + 0.2 * depth) / (sc + 1e-5)

            best_path_cost = float("inf")
            for s in start_nodes:
                if s not in graph:
                    continue
                path = astar(graph, s, code, prereq)
                if path:
                    # If path is trivial (start==goal), use own_cost instead of zero
                    if len(path) <= 1:
                        cst = own_cost
                    else:
                        cst = path_cost(graph, path)
                    if cst < best_path_cost:
                        best_path_cost = cst

            # If no path found, fall back to own_cost (still meaningful)
            if best_path_cost == float("inf"):
                best_path_cost = own_cost

            item = (best_path_cost, -sc, course.get("course_code"), course)
            if best_item is None or item < best_item:
                best_item = item

        # Select one best course for this semester
        if best_item:
            _, _, _, best_course = best_item
            sks = int(best_course.get("sks") or 0)
            if (per_semester_sks_cap is None) or (sks <= per_semester_sks_cap):
                chosen = [best_course]
                total_sks = sks
                taken.add(best_course.get("course_code"))

        schedule.append({
            "semester": sem,
            "sks": total_sks,
            "courses": [
                {
                    "course_code": c.get("course_code"),
                    "course_name_en": c.get("course_name_en") or c.get("course_name_id"),
                    "sks": c.get("sks")
                }
                for c in chosen
            ]
        })

    return {
        "name": name,
        "start_semester": current_semester,
        "schedule": schedule
    }