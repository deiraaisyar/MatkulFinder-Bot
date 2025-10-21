# model/course_recommender.py
import json
import logging
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

# Logging
logger = logging.getLogger("course_recommender")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[LOG] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class CourseRecommender:
    def __init__(
        self,
        courses_path: Union[str, Path] = "./data/cs_courses.json",
        prereq_path: Union[str, Path] = "./data/prerequisite_rules.json",
    ):
        self.courses_path = Path(courses_path)
        self.prereq_path = Path(prereq_path)

        self.courses = self._load_courses()
        self.prereq_rules = self._load_prereq_rules()

        # quick lookup by course_code for convenience
        self.course_map = {c["course_code"]: c for c in self.courses}

        # simple career -> keyword mapping (can be extended)
        self.career_keyword_map = {
            "data scientist": ["data", "machine learning", "statist", "data mining"],
            "machine learning engineer": ["machine learning", "deep learning", "ml"],
            "software engineer": ["program", "software", "object oriented", "oop"],
            "ai engineer": ["artificial", "intelligence", "ai", "deep learning"],
            "web developer": ["web", "html", "css", "javascript", "backend", "frontend"],
            "network engineer": ["network", "jaringan"],
            "cyber security": ["security", "keamanan", "kriptografi"],
            "researcher": ["research", "metodologi", "tesis", "skripsi"],
        }

    def _load_courses(self) -> List[Dict[str, Any]]:
        if not self.courses_path.exists():
            logger.debug(f"Courses file not found: {self.courses_path}")
            return []
        with open(self.courses_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Expecting list of course objects
        return data

    def _load_prereq_rules(self) -> Dict[str, Any]:
        if not self.prereq_path.exists():
            logger.debug(f"Prerequisite file not found: {self.prereq_path}")
            return {}
        with open(self.prereq_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _normalize_text(self, text: str) -> str:
        return (text or "").lower()

    def _matches_interest(self, course: Dict[str, Any], interests: List[str]) -> int:
        """Return number of interest matches (used to multiply score bonus)."""
        if not interests:
            return 0
        name_fields = " ".join(
            [
                course.get("course_name_en", ""),
                course.get("course_name_id", ""),
                course.get("type", ""),
            ]
        ).lower()
        topics = " ".join(course.get("topics", [])).lower() if course.get("topics") else ""
        matches = 0
        for it in interests:
            it_low = it.lower()
            if it_low in name_fields or it_low in topics:
                matches += 1
        return matches

    def _career_relevance(self, course: Dict[str, Any], career_target: Optional[str]) -> bool:
        if not career_target:
            return False
        career_key = career_target.lower()
        for k, keywords in self.career_keyword_map.items():
            if k in career_key or career_key in k:
                # check course name / topics for keyword presence
                hay = " ".join(
                    [
                        course.get("course_name_en", ""),
                        course.get("course_name_id", ""),
                        " ".join(course.get("topics", []) or []),
                        course.get("type", "") or "",
                    ]
                ).lower()
                for kw in keywords:
                    if kw in hay:
                        return True
        # fallback: direct keyword check
        hay = " ".join(
            [
                course.get("course_name_en", ""),
                course.get("course_name_id", ""),
                " ".join(course.get("topics", []) or []),
            ]
        ).lower()
        for token in career_key.split():
            if token in hay:
                return True
        return False

    def recommend_courses(
        self,
        courses_taken: List[str],
        interests: Optional[List[str]] = None,
        target_career: Optional[str] = None,
        sks_preference: Optional[Union[int, List[int]]] = None,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Return top_n recommended courses as JSON list.
        Rules:
         - Only consider courses that HAVE prerequisites in prerequisite_rules
         - Non-corequisite prerequisites (is_corequisite == False) MUST be already taken by user
         - Corequisite prerequisites (is_corequisite == True) are allowed (course can be recommended even if not yet taken)
         - Apply scoring based on configured weights
        """

        taken_set = set(courses_taken or [])
        interests = interests or []
        if isinstance(sks_preference, int):
            sks_pref_set = {sks_preference}
        elif isinstance(sks_preference, (list, tuple, set)):
            sks_pref_set = set(sks_preference)
        else:
            sks_pref_set = None

        evaluated = []

        for course in self.courses:
            code = course.get("course_code")
            if not code:
                continue

            # don't recommend already taken courses
            if code in taken_set:
                logger.debug(f"Skip {code}: already taken")
                continue

            # only consider non-mandatory (elective) courses
            ctype_check = (course.get("type") or "").lower()
            if "wajib" in ctype_check:
                logger.debug(f"Skip {code}: mandatory (wajib) course")
                continue

            # must have prerequisite rules entry
            prereq_entry = self.prereq_rules.get(code)
            if not prereq_entry:
                logger.debug(f"Skip {code}: no prerequisite rules")
                continue

            prereqs = prereq_entry.get("prerequisites", []) or []
            if not prereqs:
                logger.debug(f"Skip {code}: prerequisites is empty")
                continue

            # Separate coreq and non-coreq prerequisites
            non_coreq = [p["code"] for p in prereqs if not p.get("is_corequisite")]
            coreq = [p["code"] for p in prereqs if p.get("is_corequisite")]

            # Non-coreq MUST be already taken; otherwise ineligible
            if non_coreq and not set(non_coreq).issubset(taken_set):
                logger.debug(f"Skip {code}: non-coreq prereq not satisfied ({non_coreq})")
                continue

            # Begin scoring (weights per design)
            score = 0
            reasons = []

            # Prerequisite satisfied (non-coreq all taken) -> +50
            if not non_coreq or set(non_coreq).issubset(taken_set):
                score += 50
                if non_coreq:
                    reasons.append(f"Prerequisite(s) satisfied: {', '.join(non_coreq)}")
                else:
                    # If course has no non-coreq prerequisites but does have coreq, still give partial
                    reasons.append("No strict (non-coreq) prerequisites")

            # Presence of corequisite prerequisites -> +20 (allowed even if not taken)
            if coreq:
                score += 20
                reasons.append(f"Has corequisite(s): {', '.join(coreq)}")
                # bonus if coreq already taken
                if set(coreq).issubset(taken_set):
                    score += 10
                    reasons.append("Corequisite(s) already taken")

            # Interest matches: +15 per match
            interest_matches = self._matches_interest(course, interests)
            if interest_matches:
                added = 15 * interest_matches
                score += added
                reasons.append(f"Interest matches: {interest_matches} match(es)")

            # Career relevance: +10 if relevant
            if target_career and self._career_relevance(course, target_career):
                score += 10
                reasons.append(f"Relevant for career: {target_career}")

            # SKS preference: +5 if match
            if sks_pref_set is not None and course.get("sks") is not None:
                try:
                    sks_val = int(course.get("sks"))
                    if sks_val in sks_pref_set:
                        score += 5
                        reasons.append(f"SKS matches preference: {sks_val}")
                except Exception:
                    pass

            # Type bonus: Wajib Program Studi -> +5
            ctype = (course.get("type") or "").lower()
            if "wajib program studi" in ctype or "wajib prodi" in ctype:
                score += 5
                reasons.append("Wajib Program Studi (priority)")

            logger.debug(f"Evaluate {code} -> score={score}; reasons={reasons}")

            evaluated.append(
                {
                    "course_code": code,
                    "course_name_id": course.get("course_name_id"),
                    "course_name_en": course.get("course_name_en"),
                    "sks": course.get("sks"),
                    "score": score,
                    "reason": reasons,
                }
            )

        recommended = sorted(
            evaluated, key=lambda x: (-x["score"], x.get("sks") or 0, x["course_code"])
        )[:top_n]

        return recommended


if __name__ == "__main__":
    recommender = CourseRecommender(
        courses_path="data/cs_courses.json",
        prereq_path="data/prerequisite_rules.json",
    )
    sample_user = {
        "courses_taken": ["MII21-1201", "MII21-1203"],
        "interests": ["AI", "Data Science"],
        "target_career": "Data Scientist",
        "sks_preference": [2, 3],
    }
    out = recommender.recommend_courses(
        courses_taken=sample_user["courses_taken"],
        interests=sample_user["interests"],
        target_career=sample_user["target_career"],
        sks_preference=sample_user["sks_preference"],
        top_n=5,
    )
    import pprint

    pprint.pprint(out)
