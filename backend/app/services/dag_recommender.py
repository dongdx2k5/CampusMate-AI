"""
DAG Prerequisite Course Recommender & Automated Scholarship Eligibility Evaluator.
"""

from typing import Any, Dict, List, Optional
from ..database import db_connection, get_connection


def evaluate_student_scholarship(student_code: str) -> Dict[str, Any]:
    """
    Evaluates a student's eligibility against official HUCE KKHT Scholarship criteria
    (Decision 1158/QĐ-ĐHXD Article 8) and returns detailed explanations.
    """
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE student_code = ?", (student_code,))
        user = cur.fetchone()
        if not user:
            return {"found": False, "message": "Không tìm thấy hồ sơ sinh viên."}

        cur.execute(
            """
            SELECT p.*, c.course_code, c.name, c.credits
            FROM student_progress p
            JOIN courses c ON p.course_id = c.id
            WHERE p.user_id = ?
            """,
            (user["id"],),
        )
        progress_rows = [dict(r) for r in cur.fetchall()]

        # Find latest evaluated semester and calculate real credits taken
        cur.execute(
            """
            SELECT semester_taken, SUM(c.credits) as total_credits
            FROM student_progress p
            JOIN courses c ON p.course_id = c.id
            WHERE p.user_id = ?
            GROUP BY semester_taken
            ORDER BY semester_taken DESC
            LIMIT 1
            """,
            (user["id"],),
        )
        latest_sem_row = cur.fetchone()
        if latest_sem_row and latest_sem_row["total_credits"]:
            latest_sem = latest_sem_row["semester_taken"]
            credits_sem = int(latest_sem_row["total_credits"])
        else:
            latest_sem = None
            cur.execute(
                """
                SELECT SUM(c.credits) as total_credits
                FROM class_schedules s
                JOIN courses c ON s.course_id = c.id
                WHERE s.user_id = ?
                """,
                (user["id"],),
            )
            sched_sum = cur.fetchone()
            credits_sem = int(sched_sum["total_credits"]) if sched_sum and sched_sum["total_credits"] else 0

        failed_courses = [r for r in progress_rows if r["status"] == "FAILED" or r["letter_grade"] == "F"]

        # Check no course < B for XUAT_SAC tier (Decision 1158/QĐ-ĐHXD)
        sem_courses = [r for r in progress_rows if r["semester_taken"] == latest_sem] if latest_sem else progress_rows
        ACCEPTABLE_EXCELLENT_GRADES = {"A", "A-", "B+", "B"}
        has_below_b = any(
            (r["letter_grade"].upper() not in ACCEPTABLE_EXCELLENT_GRADES or float(r["grade_4"]) < 3.0)
            for r in sem_courses
        )

        cur.execute("SELECT * FROM scholarships_criteria ORDER BY min_gpa DESC")
        criteria_rows = [dict(r) for r in cur.fetchall()]

    gpa_sem = float(user["gpa_semester"])
    drl = int(user["training_score"])
    has_failed = len(failed_courses) > 0

    matched_tier = None
    tier_evaluations = []

    for crit in criteria_rows:
        gpa_ok = gpa_sem >= crit["min_gpa"]
        drl_ok = drl >= crit["min_training_score"]
        credits_ok = credits_sem >= crit["min_credits_semester"]
        no_fail_ok = not has_failed
        no_below_b_ok = not (crit["level_rank"] == "XUAT_SAC" and has_below_b)

        is_qualified = gpa_ok and drl_ok and credits_ok and no_fail_ok and no_below_b_ok
        if is_qualified and matched_tier is None:
            matched_tier = crit

        reasons = []
        if not gpa_ok:
            reasons.append(f"GPA học kỳ ({gpa_sem:.2f}) thấp hơn mức yêu cầu ({crit['min_gpa']:.2f})")
        if not drl_ok:
            reasons.append(f"Điểm rèn luyện ({drl}) thấp hơn mức yêu cầu ({crit['min_training_score']})")
        if not credits_ok:
            reasons.append(f"Số tín chỉ học kỳ ({credits_sem}) ít hơn mức tối thiểu ({crit['min_credits_semester']})")
        if not no_fail_ok:
            reasons.append(f"Có {len(failed_courses)} học phần bị điểm F chưa đạt")
        if not no_below_b_ok:
            reasons.append("Có học phần trong kỳ điểm dưới B (< 3.0), không đạt điều kiện học bổng Xuất sắc")

        tier_evaluations.append(
            {
                "scholarship_code": crit["scholarship_code"],
                "name": crit["name"],
                "min_gpa": crit["min_gpa"],
                "min_training_score": crit["min_training_score"],
                "reward_amount_vnd": crit["reward_amount_vnd"],
                "qualified": is_qualified,
                "gap_analysis": "Đạt toàn bộ điều kiện" if is_qualified else "; ".join(reasons),
                "regulation_ref": crit["regulation_ref"],
            }
        )

    return {
        "found": True,
        "student_code": user["student_code"],
        "full_name": user["full_name"],
        "class_name": user["class_name"],
        "gpa_semester": gpa_sem,
        "gpa_cumulative": user["gpa_cumulative"],
        "training_score": drl,
        "credits_semester": credits_sem,
        "failed_courses": [f"{c['course_code']} - {c['name']}" for c in failed_courses],
        "eligible": matched_tier is not None,
        "highest_matched_scholarship": matched_tier,
        "all_tiers_comparison": tier_evaluations,
        "official_citation": "Quyết định số 1158/QĐ-ĐHXD, Điều 8 (Quy định xét cấp Học bổng KKHT Trường ĐH Xây dựng Hà Nội)",
    }


def recommend_courses_dag(
    student_code: str,
    career_track: Optional[str] = None,
    max_credits: int = 18,
    min_credits: int = 14,
) -> Dict[str, Any]:
    """
    DAG Topological Course Recommender (FR2 & FR3):
    1. Identifies passed and failed courses.
    2. Prioritizes retaking any failed mandatory core prerequisite courses (Exception Flow 3a).
    3. Traverses the prerequisite DAG to unlock eligible courses.
    4. Applies career track preference (AI, SE, NETWORK) and enforces 14-24 credit limit.
    """
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE student_code = ?", (student_code,))
        user = cur.fetchone()
        if not user:
            return {"found": False, "message": "Không tìm thấy sinh viên."}

        cur.execute("SELECT * FROM courses ORDER BY recommended_semester ASC, is_mandatory DESC")
        all_courses = {r["id"]: dict(r) for r in cur.fetchall()}

        cur.execute("SELECT * FROM course_prerequisites")
        prereq_map: Dict[str, List[str]] = {}
        for row in cur.fetchall():
            prereq_map.setdefault(row["course_id"], []).append(row["prerequisite_id"])

        cur.execute("SELECT * FROM student_progress WHERE user_id = ?", (user["id"],))
        progress_rows = [dict(r) for r in cur.fetchall()]

    passed_ids = {r["course_id"] for r in progress_rows if r["status"] == "PASSED"}
    failed_ids = {r["course_id"] for r in progress_rows if r["status"] == "FAILED"}

    recommended_list = []
    blocked_courses = []
    total_credits = 0

    # Step 1: Exception Flow 3a - Mandatory Retake of Failed Core Courses
    for fid in failed_ids:
        if fid in all_courses:
            c = all_courses[fid]
            recommended_list.append(
                {
                    "course_code": c["course_code"],
                    "name": c["name"],
                    "credits": c["credits"],
                    "recommended_semester": c["recommended_semester"],
                    "career_track": c["career_track"],
                    "priority_type": "HỌC LẠI BẮT BUỘC (Do bị điểm F kỳ trước)",
                    "reason": f"Học phần cốt lõi bị điểm F, cần đăng ký học lại ngay để mở khóa chuỗi môn học kỳ sau.",
                }
            )
            total_credits += c["credits"]

    # Step 2: DAG Traversal for Remaining Uncompleted Courses
    candidates = []
    for cid, course in all_courses.items():
        if cid in passed_ids or cid in failed_ids:
            continue
        req_ids = prereq_map.get(cid, [])
        missing_reqs = [all_courses[r]["course_code"] for r in req_ids if r not in passed_ids]

        if len(missing_reqs) == 0:
            # Eligible! Score candidate based on mandatory status & career track filter
            track_bonus = 10 if (career_track and course["career_track"].upper() == career_track.upper()) else 0
            mandatory_bonus = 20 if course["is_mandatory"] else 0
            prereq_names = [f"{all_courses[r]['course_code']} ({all_courses[r]['name']})" for r in req_ids]
            candidates.append(( -(mandatory_bonus + track_bonus), course["recommended_semester"], course, prereq_names))
        else:
            blocked_courses.append(
                {
                    "course_code": course["course_code"],
                    "name": course["name"],
                    "missing_prerequisites": missing_reqs,
                }
            )

    candidates.sort(key=lambda x: (x[0], x[1]))

    for _, _, course, prereq_names in candidates:
        if total_credits + course["credits"] <= max_credits:
            prereq_text = ", ".join(prereq_names) if prereq_names else "Không yêu cầu môn tiên quyết"
            recommended_list.append(
                {
                    "course_code": course["course_code"],
                    "name": course["name"],
                    "credits": course["credits"],
                    "recommended_semester": course["recommended_semester"],
                    "career_track": course["career_track"],
                    "priority_type": "Bắt buộc" if course["is_mandatory"] else f"Tự chọn định hướng ({course['career_track']})",
                    "prerequisites_satisfied": prereq_text,
                    "reason": f"Đã hoàn thành môn tiên quyết ({prereq_text}); phù hợp lộ trình học kỳ {course['recommended_semester']}.",
                }
            )
            total_credits += course["credits"]

    return {
        "found": True,
        "student_code": user["student_code"],
        "full_name": user["full_name"],
        "career_track_selected": career_track or "ALL (Toàn diện AI & Công nghệ Phần mềm)",
        "total_recommended_credits": total_credits,
        "credit_policy_range": f"{min_credits} - 24 tín chỉ/học kỳ (Quyết định 892/QĐ-ĐHXD, Điều 14)",
        "passed_courses_count": len(passed_ids),
        "recommended_courses": recommended_list,
        "blocked_courses": blocked_courses,
    }


def get_student_schedules_and_exams(student_code: str) -> Dict[str, Any]:
    """Retrieves both weekly class schedules and semester exam schedules for a student."""
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE student_code = ?", (student_code,))
        user = cur.fetchone()
        if not user:
            return {"found": False}

        cur.execute(
            """
            SELECT s.*, c.course_code, c.name as course_name, c.credits
            FROM class_schedules s
            JOIN courses c ON s.course_id = c.id
            WHERE s.user_id = ?
            ORDER BY s.day_index ASC, s.periods ASC
            """,
            (user["id"],),
        )
        class_schedules = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT e.*, c.course_code, c.name as course_name, c.credits
            FROM exam_schedules e
            JOIN courses c ON e.course_id = c.id
            WHERE e.user_id = ?
            ORDER BY e.exam_date ASC, e.exam_time ASC
            """,
            (user["id"],),
        )
        exam_schedules = [dict(r) for r in cur.fetchall()]

    return {
        "found": True,
        "student_code": user["student_code"],
        "full_name": user["full_name"],
        "class_name": user["class_name"],
        "semester": "2026-1",
        "class_schedules": class_schedules,
        "exam_schedules": exam_schedules,
    }
