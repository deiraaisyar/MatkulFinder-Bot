import json
from typing import List, Optional, Dict, Any, Union, Tuple

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_knowledge() -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, List[str]], Dict[str, List[str]]]:
    """Load all knowledge sources from ./data"""
    courses = load_json("data/cs_courses.json") or load_json("data/courses.json")
    prereqs = load_json("data/prerequisite_rules.json") or load_json("data/prerequisites.json")
    career_keywords = load_json("data/career_keywords.json")
    lab_preferences = load_json("data/lab_preferences.json")
    # Normalize expected types
    if not isinstance(courses, list):
        courses = []
    if not isinstance(prereqs, dict):
        prereqs = {}
    if not isinstance(career_keywords, dict):
        career_keywords = {}
    if not isinstance(lab_preferences, dict):
        lab_preferences = {}
    return courses, prereqs, career_keywords, lab_preferences

def to_int(val: Union[int, str]) -> Optional[int]:
    try:
        return int(val)
    except Exception:
        return None

def expand_semester_pref(pref: Union[int, str]) -> List[int]:
    """Numeric-only semester reference: returns [n] or []."""
    if isinstance(pref, int):
        return [pref]
    n = to_int(pref)
    return [n] if n is not None else []

def expand_next_from_current(cur: Union[int, str]) -> List[int]:
    """Numeric-only current_semester: returns [n+1] if 1 <= n < 8 else []."""
    n = cur if isinstance(cur, int) else to_int(cur)
    if n is None:
        return []
    return [n + 1] if 1 <= n < 8 else []

def get_lab_category(course_type) -> Optional[str]:
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

def matches_interest(course: Dict[str, Any], interests: List[str]) -> int:
    haystack = " ".join([
        course.get("course_name_en", ""),
        course.get("course_name_id", ""),
        course.get("type", ""),
        " ".join(course.get("topics", []) or []),
    ]).lower()
    return sum(1 for i in interests if str(i).lower() in haystack)

def is_relevant_to_career(course: Dict[str, Any], target, career_keywords: Dict[str, List[str]]) -> bool:
    target = (target or "").lower()
    haystack = " ".join([
        course.get("course_name_en", ""),
        course.get("course_name_id", ""),
        " ".join(course.get("topics", []) or []),
        course.get("type", "") or "",
    ]).lower()
    for career, keywords in career_keywords.items():
        if career in target or target in career:
            if any(kw in haystack for kw in keywords):
                return True

def recommend(
    taken: List[str],
    interests: List[str],
    career: str,
    top_n: int = 3,
    sks_preference: Optional[Union[int, List[int]]] = None,
    sks_must_match: bool = False,
    semester_preference: Optional[Union[int, str, List[Union[int, str]]]] = None,
    current_semester: Optional[Union[int, str]] = None,
) -> List[Dict[str, Any]]:
    """Top-N recommended elective courses based on simple rule-based logic."""
    courses, prereq_rules, career_keywords, lab_preferences = load_knowledge()

    taken_set = set(taken)
    recommendations: List[Dict[str, Any]] = []

    # Prepare SKS preference set
    if isinstance(sks_preference, int):
        sks_pref_set = {sks_preference}
    elif isinstance(sks_preference, (list, tuple, set)):
        sks_pref_set = set(sks_preference)
    else:
        sks_pref_set = None

    # Semester preferences (numeric-only)
    sem_pref_acc: List[int] = []
    if semester_preference is not None:
        if isinstance(semester_preference, (list, tuple, set)):
            for item in semester_preference:
                sem_pref_acc.extend(expand_semester_pref(item))
        else:
            sem_pref_acc.extend(expand_semester_pref(semester_preference))
    elif current_semester is not None:
        sem_pref_acc.extend(expand_next_from_current(current_semester))
    sem_pref_set = set(sem_pref_acc) if sem_pref_acc else None

    # Lab labels for reasons
    lab_labels = {
        "algkom": "Algoritma & Komputasi",
        "rpld": "Rekayasa Perangkat Lunak & Data",
        "ai": "Sistem Cerdas",
        "skj": "Sistem Komputer & Jaringan",
    }

    for course in courses:
        code = course.get("course_code")
        if not code or code in taken_set:
            continue
        if "wajib" in (course.get("type") or "").lower():
            continue  # elective-only

        rules = prereq_rules.get(code) if isinstance(prereq_rules, dict) else None
        if not rules:
            continue
        prereqs = rules.get("prerequisites", []) or []
        if not prereqs:
            continue

        non_coreq = [p.get("code") for p in prereqs if p and not p.get("is_corequisite")]
        coreq = [p.get("code") for p in prereqs if p and p.get("is_corequisite")]

        if non_coreq and not set(non_coreq).issubset(taken_set):
            continue  # must have taken all non-coreq prereqs

        # Semester filtering
        if sem_pref_set is not None:
            course_sems = course.get("semesters") or []
            try:
                course_sems_set = {int(s) for s in course_sems if s is not None}
            except Exception:
                course_sems_set = {s for s in course_sems if isinstance(s, int)}
            if course_sems_set and course_sems_set.isdisjoint(sem_pref_set):
                continue

        # Strict SKS filtering
        if sks_must_match and sks_pref_set is not None:
            try:
                sks_val = int(course.get("sks")) if course.get("sks") is not None else None
            except Exception:
                sks_val = None
            if sks_val is None or sks_val not in sks_pref_set:
                continue

        score = 0
        reasons: List[str] = []

        # Prereq satisfied reward
        if not non_coreq or set(non_coreq).issubset(taken_set):
            score += 50
            if non_coreq:
                reasons.append(f"Prerequisite(s) satisfied: {', '.join(non_coreq)}")
            else:
                reasons.append("No strict (non-coreq) prerequisites")

        # Interests
        interest_match = matches_interest(course, interests)
        if interest_match:
            score += 15 * interest_match
            reasons.append(f"{interest_match} interest match(es)")

        # Career relevance
        if is_relevant_to_career(course, career, career_keywords):
            score += 20
            reasons.append(f"Relevant for {career}")

        # Corequisite bonus
        if coreq:
            score += 20
            reasons.append(f"Has corequisite(s): {', '.join(coreq)}")
            if set(coreq).issubset(taken_set):
                score += 10
                reasons.append("Corequisite(s) already taken")

        # Lab alignment
        lab_cat = get_lab_category(course.get("type"))
        lab_pref: List[str] = []
        ck = (career or "").lower()
        for k, v in lab_preferences.items():
            if k in ck or ck in k:
                lab_pref = v
                break
        if lab_cat and lab_cat in lab_pref:
            score += 10
            reasons.append(f"Aligned with preferred lab: {lab_labels.get(lab_cat)}")

        # SKS preference
        if sks_pref_set is not None and course.get("sks") is not None:
            try:
                sv = int(course.get("sks"))
                if sv in sks_pref_set:
                    score += 5
                    reasons.append(f"SKS matches preference: {sv}")
            except Exception:
                pass

        # Semester preference scoring (+15 on match)
        if sem_pref_set is not None:
            course_sems = course.get("semesters") or []
            try:
                cset = {int(s) for s in course_sems if s is not None}
            except Exception:
                cset = {s for s in course_sems if isinstance(s, int)}
            if cset and not cset.isdisjoint(sem_pref_set):
                score += 15
                inter = ", ".join(str(s) for s in sorted(cset & sem_pref_set))
                reasons.append("Semester matches preference: " + inter)

        if score > 0:
            recommendations.append({
                "course_code": code,
                "course_name_en": course.get("course_name_en"),
                "score": score,
                "reasons": reasons,
            })

    return sorted(recommendations, key=lambda x: -x["score"])[: 3]