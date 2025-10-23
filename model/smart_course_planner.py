from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, FrozenSet, Tuple, Union
import json
import heapq
import sys
from pathlib import Path as _P
sys.path.append(str(_P(__file__).resolve().parents[1]))
from model.course_recommender import CourseRecommender  

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COURSES_PATH = DATA_DIR / "cs_courses.json"
PREREQ_PATH = DATA_DIR / "prerequisite_rules.json"


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class CoursePlanner:
    """
    Greedy per-semester elective planner (structured to match repo data).
    - Plans from next semester (current+1) until semester 8
    - Picks only electives (excludes any course whose type contains 'wajib')
    - Honors prerequisites (non-coreq must be taken already)
    - Respects semester availability if provided in course["semesters"]
    - Ranks candidates by a simple score: interests + career relevance + lab preference
    """

    def __init__(self, courses_path: Path = COURSES_PATH, prereq_path: Path = PREREQ_PATH) -> None:
        self.courses = _load_json(courses_path)
        self.prereq = _load_json(prereq_path)
        self.rec = CourseRecommender(courses_path=courses_path, prereq_path=prereq_path)

        # fast lookup
        self.course_by_code: Dict[str, Dict[str, Any]] = {
            c.get("course_code"): c for c in self.courses if c.get("course_code")
        }
        # Per-semester SKS caps are provided at runtime by the user (comma-separated or list)

    def _is_elective(self, course: Dict[str, Any]) -> bool:
        ctype = (course.get("type") or "").lower()
        return "wajib" not in ctype

    def _offered_in_semester(self, course: Dict[str, Any], sem: int) -> bool:
        sems = course.get("semesters") or []
        if not sems:
            # if data missing, allow
            return True
        try:
            sems_int = {int(s) for s in sems if s is not None}
        except Exception:
            sems_int = {s for s in sems if isinstance(s, int)}
        return sem in sems_int if sems_int else True

    def _prereq_ok(self, code: str, taken: Set[str]) -> bool:
        entry = self.prereq.get(code)
        if not entry:
            # Treat missing entry as no strict prerequisites
            return True
        prereqs = entry.get("prerequisites", []) or []
        if not prereqs:
            # No prerequisites -> eligible
            return True
        non_coreq = [p["code"] for p in prereqs if not p.get("is_corequisite")]
        return set(non_coreq).issubset(taken)

    def _score(self, course: Dict[str, Any], interests: List[str], career_goal: Optional[str]) -> int:
        score = 0
        # interests
        matches = self.rec._matches_interest(course, interests or [])
        score += 15 * matches

        # career relevance
        if career_goal and self.rec._career_relevance(course, career_goal):
            score += 10

        # lab preference
        lab_cat = self.rec._lab_category(course.get("type"))
        lab_pref = self.rec._lab_preferences_for_career(career_goal)
        if lab_cat and lab_pref and lab_cat in lab_pref:
            idx = lab_pref.index(lab_cat)
            weights = [20, 12, 6, 3]
            score += weights[idx] if idx < len(weights) else 2
        return score

    def _pick_for_semester(
        self,
        sem: int,
        taken: Set[str],
        interests: List[str],
        career_goal: Optional[str],
        max_sks: int,
    ) -> List[Dict[str, Any]]:
        # candidates: elective, not taken, offered this sem, prereq ok
        candidates: List[Dict[str, Any]] = []
        for c in self.courses:
            code = c.get("course_code")
            if not code or code in taken:
                continue
            if not self._is_elective(c):
                continue
            if not self._offered_in_semester(c, sem):
                continue
            if not self._prereq_ok(code, taken):
                continue
            candidates.append(c)

        # rank by score desc
        candidates.sort(key=lambda x: self._score(x, interests, career_goal), reverse=True)

        picked: List[Dict[str, Any]] = []
        total_sks = 0
        for c in candidates:
            try:
                sks = int(c.get("sks") or 0)
            except Exception:
                sks = 0
            if sks <= 0:
                continue
            if total_sks + sks > max_sks:
                continue
            picked.append(c)
            total_sks += sks
        return picked

    # ---------- A* based full-planner (from next semester to 8) ----------
    def _candidate_courses_for_semester(self, sem: int, taken_prev: Set[str]) -> List[Dict[str, Any]]:
        out = []
        for c in self.courses:
            code = c.get("course_code")
            if not code:
                continue
            if not self._is_elective(c):
                continue
            if not self._offered_in_semester(c, sem):
                continue
            if not self._prereq_ok(code, taken_prev):
                continue
            out.append(c)
        return out


    def plan_until_graduation_astar(
        self,
        name: str,
        courses_taken: List[str],
        interests: List[str],
        career_goal: Optional[str],
        current_semester: int,
        per_semester_caps: Optional[Union[str, List[int]]] = None,
        top_candidates: int = 15,
        max_expansions: int = 20000,
    ) -> Dict[str, Any]:
        """
        Use A* search to build an elective-only plan from next semester up to semester 8.

        State = (sem, used_sks, planned_prev, planned_cur)
          - sem: current semester number being planned
          - used_sks: SKS already selected in this semester
          - planned_prev: frozenset of course codes chosen in earlier semesters
          - planned_cur: frozenset of course codes chosen in the current semester

        Transitions:
          - add one eligible course to current semester (respect SKS limit)
          - advance to next semester (sem += 1), flushing planned_cur into planned_prev

        Goal: sem == 8 (passed semester 7)
        Cost: sum over steps of (C - score(course)) for adds, with C=200.
        Heuristic: 0 (admissible, keeps algorithm correct)
        """
        start_sem = int(current_semester) + 1
        # Build per-semester SKS caps mapping from user-provided sequence, starting at start_sem
        caps_map: Dict[int, int] = {}
        caps_list: List[int] = []
        if isinstance(per_semester_caps, str):
            raw = [p.strip() for p in per_semester_caps.split(",")]
            for p in raw:
                try:
                    n = int(p)
                    if n > 0:
                        caps_list.append(n)
                except Exception:
                    continue
        elif isinstance(per_semester_caps, (list, tuple)):
            for p in per_semester_caps:
                try:
                    n = int(p)
                    if n > 0:
                        caps_list.append(n)
                except Exception:
                    continue
        # Assign sequentially to semesters start_sem..7
        for idx, sem in enumerate(range(start_sem, 8)):
            if idx < len(caps_list):
                caps_map[sem] = caps_list[idx]
        start_state: Tuple[int, int, FrozenSet[str], FrozenSet[str]] = (start_sem, 0, frozenset(), frozenset())

        def goal(state: Tuple[int, int, FrozenSet[str], FrozenSet[str]]) -> bool:
            sem, _used, _prev, _cur = state
            return sem >= 8

        def heuristic(_state: Tuple[int, int, FrozenSet[str], FrozenSet[str]]) -> int:
            return 0

        # Priority queue entries: (f, state)
        open_heap: List[Tuple[int, Tuple[int, int, FrozenSet[str], FrozenSet[str]]]] = []
        heapq.heappush(open_heap, (0, start_state))
        came_from: Dict[Tuple[int, int, FrozenSet[str], FrozenSet[str]], Tuple[Tuple[int, int, FrozenSet[str], FrozenSet[str]], Tuple[str, Optional[str]]]] = {}
        # action tuple = ("add", code) or ("advance", None)
        g_cost: Dict[Tuple[int, int, FrozenSet[str], FrozenSet[str]], int] = {start_state: 0}

        expansions = 0
        ADVANCE_BASE = 1000  # per-semester baseline cost; reduced by semester 'fit'
        SKS_BONUS_PER_SKS = 60  # stronger incentive to fill SKS, enabling later semesters to be used

        while open_heap and expansions < max_expansions:
            _, state = heapq.heappop(open_heap)
            expansions += 1
            sem, used, prev_set, cur_set = state

            if goal(state):
                break

            # Transition 1: add an eligible course in current semester
            taken_prev = set(courses_taken or []) | set(prev_set)
            candidates = self._candidate_courses_for_semester(sem, taken_prev)
            # Remove those already chosen in prev or cur
            chosen_all = set(prev_set) | set(cur_set)
            candidates = [c for c in candidates if c.get("course_code") not in chosen_all]
            # Rank top-K by score
            candidates.sort(key=lambda x: self._score(x, interests or [], career_goal), reverse=True)
            if top_candidates > 0:
                candidates = candidates[:top_candidates]

            for c in candidates:
                try:
                    sks = int(c.get("sks") or 0)
                except Exception:
                    sks = 0
                cap = caps_map.get(sem, 20)
                if sks <= 0 or used + sks > cap:
                    continue
                code = c.get("course_code")
                if not code:
                    continue
                # adding within a semester is free; reward applied when advancing
                step_cost = 0
                new_state: Tuple[int, int, FrozenSet[str], FrozenSet[str]] = (
                    sem,
                    used + sks,
                    prev_set,
                    frozenset(set(cur_set) | {code}),
                )
                tentative_g = g_cost[state] + step_cost
                if tentative_g < g_cost.get(new_state, float("inf")):
                    g_cost[new_state] = tentative_g
                    came_from[new_state] = (state, ("add", code))
                    f = tentative_g + heuristic(new_state)
                    heapq.heappush(open_heap, (f, new_state))

            # Transition 2: advance semester
            next_state: Tuple[int, int, FrozenSet[str], FrozenSet[str]] = (
                sem + 1,
                0,
                frozenset(set(prev_set) | set(cur_set)),
                frozenset(),
            )
            # advancing pays baseline cost reduced by the total score and SKS of this semester
            semester_score = 0
            semester_sks = 0
            for code in cur_set:
                course = self.course_by_code.get(code)
                if course:
                    semester_score += self._score(course, interests or [], career_goal)
                    try:
                        semester_sks += int(course.get("sks") or 0)
                    except Exception:
                        pass
            effective = semester_score + SKS_BONUS_PER_SKS * semester_sks
            step_cost = max(0, ADVANCE_BASE - effective)
            tentative_g = g_cost[state] + step_cost
            if tentative_g < g_cost.get(next_state, float("inf")):
                g_cost[next_state] = tentative_g
                came_from[next_state] = (state, ("advance", None))
                f = tentative_g + heuristic(next_state)
                heapq.heappush(open_heap, (f, next_state))

        # pick best goal-like state: among states with sem>=8 and minimal g
        goal_states = [(s, g) for s, g in g_cost.items() if s[0] >= 8]
        if goal_states:
            best_state = min(goal_states, key=lambda x: x[1])[0]
        else:
            # Fallback: pick the furthest semester reached (max sem), then lowest cost
            best_state = min(g_cost.keys(), key=lambda s: (-s[0], g_cost[s]))

        # Reconstruct actions
        actions: List[Tuple[str, Optional[str], int]] = []  # (action, code, sem_at_action)
        node = best_state
        while node in came_from:
            prev, act = came_from[node]
            sem_at = prev[0]
            actions.append((act[0], act[1], sem_at))
            node = prev
        actions.reverse()

        # Build schedule map from actions
        schedule_map: Dict[int, List[Dict[str, Any]]] = {s: [] for s in range(start_sem, 8)}
        chosen_codes: Set[str] = set()
        for typ, code, sem_at in actions:
            if typ != "add" or code is None:
                continue
            if sem_at < start_sem or sem_at > 7:
                continue
            if code in chosen_codes:
                continue
            course = self.course_by_code.get(code)
            if not course:
                continue
            schedule_map[sem_at].append(course)
            chosen_codes.add(code)

        # Compose final schedule array
        schedule: List[Dict[str, Any]] = []
        for sem in range(start_sem, 8):
            courses = schedule_map.get(sem, [])
            total_sks = 0
            for c in courses:
                try:
                    total_sks += int(c.get("sks") or 0)
                except Exception:
                    pass
            schedule.append({"semester": sem, "courses": courses, "sks": total_sks})

        return {
            "name": name,
            "start_semester": current_semester,
            "schedule": schedule,
        }

    def plan_until_graduation(
        self,
        name: str,
        courses_taken: List[str],
        interests: List[str],
        career_goal: Optional[str],
        current_semester: int,
        per_semester_caps: Optional[Union[str, List[int]]] = None,
    ) -> Dict[str, Any]:
        """Default to A* planner for full plan until semester 8."""
        return self.plan_until_graduation_astar(
            name=name,
            courses_taken=courses_taken,
            interests=interests,
            career_goal=career_goal,
            current_semester=current_semester,
            per_semester_caps=per_semester_caps,
        )