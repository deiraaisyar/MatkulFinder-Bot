import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

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

        # simple career -> keyword mapping (can be extended)
        self.career_keyword_map = {
            "data scientist": ["data", "machine learning", "statist", "data mining", 'sistem cerdas'],
            "machine learning engineer": ["machine learning", "deep learning", "ml"],
            "software engineer": ["program", "software", "object oriented", "oop"],
            "ai engineer": ["artificial", "intelligence", "ai", "deep learning"],
            "web developer": ["web", "html", "css", "javascript", "backend", "frontend"],
            "network engineer": ["network", "jaringan"],
            "cyber security": ["security", "keamanan", "kriptografi"],
            "business": ["business", "bisnis", "startup", "entrepreneur", "wirausaha", "marketing", "pemasaran", "manajemen", "management", "finance", "keuangan", "proposal", "rencana bisnis", "budget", "operational", "operation", "ethic", "etika"],
            "business analyst": ["business", "bisnis", "analyst", "analisis", "data", "requirement", "kebutuhan", "process", "proses", "kpi"],
            "product manager": ["product", "produk", "ui", "ux", "user", "requirement", "roadmap", "design thinking"],
            "project manager": ["project", "proyek","manajemen proyek", "scheduling", "estimasi", "risk", "resiko", "anggaran", "budget",],
            "data engineer": ["data pipeline", "data warehouse", "big data", "spark", "hadoop", "stream", "kafka", "etl"],
            "cloud engineer": ["cloud", "aws", "azure", "gcp", "microservice", "docker", "kubernetes", "devops"],
            "devops engineer": ["devops engineer", "ci/cd", "kubernetes", "docker", "monitoring", "orchestration", "scalable", "scalability"],
            "mobile developer": ["mobile developer", "android", "ios", "kotlin", "swift", "react native", "flutter"],
            "game developer": ["game developer", "grafika", "graphics", "unity", "unreal", "3d", "animasi"],
            "blockchain developer": ["blockchain developer", "smart contract", "ethereum", "bitcoin", "cryptography", "kriptografi"],
            "database administrator": ["database", "sql", "normalisasi", "query", "optimisasi", "index"],
            "frontend developer": ["frontend", "react", "vue", "css", "javascript", "ui"],
            "backend developer": ["backend", "api", "rest", "microservice", "database", "server"],
            "full stack developer": ["frontend", "backend", "full stack", "web"],
            "ui/ux designer": ["ui", "ux", "user experience", "user interface", "design"],
            "qa engineer": ["quality", "testing", "unit test", "automation", "assurance"],
            "security analyst": ["security", "keamanan", "network", "forensik", "audit"],
            "computer vision engineer": ["vision", "penglihatan komputer", "image", "citra"],
            "nlp engineer": ["nlp", "natural language", "bahasa alami", "text"],
        }

        # Preferred lab categories per career (ordered by priority)
        # Lab category codes:
        #  - algkom: Pilihan Lab Algoritma dan Komputasi
        #  - rpld:   Pilihan Lab Rekayasa Perangkat Lunak dan Data
        #  - ai:     Pilihan Lab Sistem Cerdas
        #  - skj:    Pilihan Lab Sistem Komputer dan Jaringan
        self.lab_labels = {
            "algkom": "Algoritma & Komputasi",
            "rpld": "Rekayasa Perangkat Lunak & Data",
            "ai": "Sistem Cerdas",
            "skj": "Sistem Komputer & Jaringan",
        }
        self.career_lab_preferences = {
            # Web/UI/Frontend oriented
            "frontend developer": ["rpld", "algkom", "skj"],
            "ui/ux designer": ["rpld", "algkom"],
            "web developer": ["rpld", "algkom"],
            "full stack developer": ["rpld", "algkom", "skj"],
            "backend developer": ["rpld", "skj", "algkom"],

            # Data/AI oriented
            "data scientist": ["ai", "algkom", "rpld"],
            "data engineer": ["rpld", "skj"],
            "ai engineer": ["ai", "algkom", "rpld"],
            "machine learning engineer": ["ai", "algkom", "rpld"],
            "computer vision engineer": ["ai", "algkom"],
            "nlp engineer": ["ai", "algkom"],

            # Infra/Security oriented
            "devops engineer": ["skj", "rpld"],
            "cloud engineer": ["skj", "rpld"],
            "security analyst": ["skj", "rpld"],
            "network engineer": ["skj"],

            # Product/Business/QA
            "product manager": ["rpld", "algkom"],
            "project manager": ["rpld"],
            "business": ["rpld"],
            "business analyst": ["rpld"],
            "qa engineer": ["rpld"],

            # Others
            "mobile developer": ["rpld", "algkom"],
            "game developer": ["algkom", "ai"],
            "database administrator": ["rpld", "skj"],
            "blockchain developer": ["skj", "rpld"],
            "software engineer": ["rpld", "algkom"],
        }

    def _lab_category(self, course_type: Optional[str]) -> Optional[str]:
        ct = (course_type or "").lower()
        if not ct:
            return None
        if "algoritma" in ct or "komputasi" in ct:
            return "algkom"
        if "rekayasa perangkat lunak" in ct or " rpl" in ct or " data" in ct:
            # ' data' avoids matching unrelated 'metadata' etc., adequate for our dataset
            return "rpld"
        if "sistem cerdas" in ct or "kecerdasan" in ct or "intelligent" in ct:
            return "ai"
        if "sistem komputer" in ct or "jaringan" in ct or "network" in ct:
            return "skj"
        return None

    def _lab_preferences_for_career(self, career_target: Optional[str]) -> Optional[List[str]]:
        if not career_target:
            return None
        key = career_target.lower()
        # match like in _career_relevance
        for k in self.career_lab_preferences.keys():
            if k in key or key in k:
                return self.career_lab_preferences[k]
        return None

    def _load_courses(self) -> List[Dict[str, Any]]:
        if not self.courses_path.exists():
            return []
        with open(self.courses_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Expecting list of course objects
        return data

    def _load_prereq_rules(self) -> Dict[str, Any]:
        if not self.prereq_path.exists():
            return {}
        with open(self.prereq_path, "r", encoding="utf-8") as f:
            return json.load(f)

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
        semester_preference: Optional[Union[int, str, List[Union[int, str]]]] = None,
        current_semester: Optional[Union[int, str]] = None,
        sks_must_match: bool = False,
        top_n: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Return top_n recommended courses as JSON list.
        Rules:
         - Only consider courses that HAVE prerequisites in prerequisite_rules
         - Non-corequisite prerequisites (is_corequisite == False) MUST be already taken by user
         - Corequisite prerequisites (is_corequisite == True) are allowed (course can be recommended even if not yet taken)
         - Apply scoring based on configured weights
                Additional inputs:
                 - semester_preference: preferred semesters (e.g., 5, "gasal", [5,7])
                 - current_semester: student's current semester (int or string like "gasal"/"genap").
                     If provided, it will be merged with semester_preference for filtering and scoring.
                """

        taken_set = set(courses_taken or [])
        interests = interests or []
        if isinstance(sks_preference, int):
            sks_pref_set = {sks_preference}
        elif isinstance(sks_preference, (list, tuple, set)):
            sks_pref_set = set(sks_preference)
        else:
            sks_pref_set = None

        # Normalize semester preference -> set[int]
        def _to_int(val: Union[int, str]) -> Optional[int]:
            try:
                return int(val)
            except Exception:
                return None

        def _expand_semester_pref(pref: Union[int, str]) -> List[int]:
            if isinstance(pref, int):
                return [pref]
            p = str(pref or "").strip().lower()
            # Support synonyms for odd/even
            if p in {"gasal", "ganjil", "odd"}:
                return [1, 3, 5, 7]
            if p in {"genap", "even"}:
                return [2, 4, 6, 8]
            n = _to_int(p)
            return [n] if n is not None else []

        def _expand_next_from_current(cur: Union[int, str]) -> List[int]:
            """Given current semester, return the next semester(s).
            - If integer n in [1..7], returns [n+1]. If n>=8 or invalid, returns [].
            - If 'gasal'/odd -> returns all even semesters [2,4,6,8].
            - If 'genap'/even -> returns all odd semesters [1,3,5,7].
            - If numeric string, treated as integer.
            """
            if isinstance(cur, int):
                try:
                    n = int(cur)
                    return [n + 1] if 1 <= n < 8 else []
                except Exception:
                    return []
            p = str(cur or "").strip().lower()
            if p in {"gasal", "ganjil", "odd"}:
                return [2, 4, 6, 8]
            if p in {"genap", "even"}:
                return [1, 3, 5, 7]
            n = _to_int(p)
            if n is not None:
                return [n + 1] if 1 <= n < 8 else []
            return []

        # Build semester set for filtering/scoring:
        # - If semester_preference is provided, use it as-is.
        # - Else if current_semester is provided, target the next semester(s).
        sem_pref_acc: List[int] = []
        if semester_preference is not None:
            if isinstance(semester_preference, (list, tuple, set)):
                for item in semester_preference:
                    sem_pref_acc.extend(_expand_semester_pref(item))
            else:
                sem_pref_acc.extend(_expand_semester_pref(semester_preference))
        elif current_semester is not None:
            sem_pref_acc.extend(_expand_next_from_current(current_semester))

        sem_pref_set: Optional[set]
        sem_pref_set = set(sem_pref_acc) if sem_pref_acc else None

        evaluated = []

        for course in self.courses:
            code = course.get("course_code")
            if not code:
                continue

            # don't recommend already taken courses
            if code in taken_set:
                continue

            # only consider non-mandatory (elective) courses
            ctype_check = (course.get("type") or "").lower()
            if "wajib" in ctype_check:
                continue

            # must have prerequisite rules entry
            prereq_entry = self.prereq_rules.get(code)
            if not prereq_entry:
                continue

            prereqs = prereq_entry.get("prerequisites", []) or []
            if not prereqs:
                continue

            # Separate coreq and non-coreq prerequisites
            non_coreq = [p["code"] for p in prereqs if not p.get("is_corequisite")]
            coreq = [p["code"] for p in prereqs if p.get("is_corequisite")]

            # Non-coreq MUST be already taken; otherwise ineligible
            if non_coreq and not set(non_coreq).issubset(taken_set):
                continue

            # Semester filtering (if preference provided and the course has semester info)
            course_sems = course.get("semesters") or []
            course_sems_set = set()
            try:
                course_sems_set = {int(s) for s in course_sems if s is not None}
            except Exception:
                # if data contains non-integers, ignore conversion failures
                course_sems_set = {s for s in course_sems if isinstance(s, int)}

            if sem_pref_set is not None and course_sems_set:
                if course_sems_set.isdisjoint(sem_pref_set):
                    continue

            # Strict SKS filtering (if requested)
            if sks_must_match and sks_pref_set is not None:
                try:
                    sks_val = int(course.get("sks")) if course.get("sks") is not None else None
                except Exception:
                    sks_val = None
                if sks_val is None or sks_val not in sks_pref_set:
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

            # Lab preference scoring: prioritize labs aligned with the target career
            lab_cat = self._lab_category(course.get("type"))
            lab_pref = self._lab_preferences_for_career(target_career)
            if lab_cat and lab_pref:
                if lab_cat in lab_pref:
                    idx = lab_pref.index(lab_cat)
                    weights = [20, 12, 6, 3]
                    bonus = weights[idx] if idx < len(weights) else 2
                    score += bonus
                    pretty = self.lab_labels.get(lab_cat, lab_cat)
                    reasons.append(
                        f"Lab preference match: {pretty} (priority {idx + 1}) for {target_career}"
                    )

            # Semester preference scoring: +15 for a match (if both sides known)
            if sem_pref_set is not None and course_sems_set:
                if not course_sems_set.isdisjoint(sem_pref_set):
                    score += 15
                    reasons.append(
                        "Semester matches preference: "
                        + ", ".join(str(s) for s in sorted(course_sems_set & sem_pref_set))
                    )
            elif sem_pref_set is not None and not course_sems_set:
                # No semester info available; do not filter, but add a note
                reasons.append("Semester info unavailable")

            # Type bonus: Wajib Program Studi -> +5
            ctype = (course.get("type") or "").lower()
            if "wajib program studi" in ctype or "wajib prodi" in ctype:
                score += 5
                reasons.append("Wajib Program Studi (priority)")

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