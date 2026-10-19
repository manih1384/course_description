"""
Transcript Parser & Course Matcher
Extracts semester-by-semester courses and credit hours from academic transcripts
(e.g., University of Tehran English transcripts) and matches them against the course catalog.
Strictly preserves privacy: excludes student grades, GPAs, and personal identifiers.
"""

import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from difflib import SequenceMatcher

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
COURSES_DIR = DATA_DIR / "courses"
CATALOG_FILE = DATA_DIR / "courses.json"
ALIASES_FILE = DATA_DIR / "aliases.json"


def normalize_title(title):
    """Normalize a course title string for fuzzy comparison."""
    if not title:
        return ""
    t = title.strip().lower()
    t = t.replace("&", " and ")
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_to_slug(title):
    """Convert title to a clean slug ID."""
    norm = normalize_title(title)
    return re.sub(r"\s+", "_", norm)


def load_aliases():
    """Load manual course alias mappings."""
    if not ALIASES_FILE.exists():
        return {}
    try:
        with open(ALIASES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("aliases", {})
    except Exception as e:
        print(f"[Warning] Could not load aliases from {ALIASES_FILE}: {e}")
        return {}


def load_catalog():
    """Load the full catalog of courses."""
    catalog = {}
    if CATALOG_FILE.exists():
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        except Exception:
            pass
    if COURSES_DIR.exists():
        for p in COURSES_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    cid = c.get("id", p.stem)
                    catalog[cid] = c
            except Exception:
                pass
    return catalog


def extract_transcript_text(transcript_path):
    """Extract text layout from transcript PDF or read text file."""
    p = Path(transcript_path)
    if not p.exists():
        raise FileNotFoundError(f"Transcript file not found: {p}")

    if p.suffix.lower() == ".pdf":
        pdftotext_bin = shutil.which("pdftotext") or "/usr/bin/pdftotext"
        if not os.path.exists(pdftotext_bin):
            raise EnvironmentError("pdftotext binary not found. Please install poppler-utils.")
        res = subprocess.run(
            [pdftotext_bin, "-layout", str(p), "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {res.stderr}")
        return res.stdout
    else:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def parse_transcript(transcript_path):
    """
    Parse a University of Tehran transcript layout into structured semesters and courses.
    Returns:
        semesters: list of semester dicts with courses
        metadata: non-sensitive metadata (degree level, major, faculty) if detectable
    """
    raw_text = extract_transcript_text(transcript_path)
    pages = raw_text.split("\x0c")

    # Detect college/faculty & major (general academic context, strictly no grades/GPA/ID)
    major_match = re.search(r"Major\s*:\s*([^\n\r]+)", pages[0])
    major = major_match.group(1).strip() if major_match else "Computer Engineering"
    level_match = re.search(r"Level\s*:\s*([^\n\r]+)", pages[0])
    degree_level = level_match.group(1).strip() if level_match else "Bachelor"

    # Collect left and right column lines across all pages continuously
    header_footer_keywords = [
        "In The Name Of God",
        "University of Tehran",
        "Transcript of University Grades",
        "Student No :",
        "Faculty :",
        "First Name :",
        "Last Name :",
        "ID.No :",
        "GPA :",
        "Date of Birth :",
        "Level :",
        "Workshop Titles:",
        "GENERAL DIRECTOR OF ACADEMIC AFFAIRS",
        "signed and sealed",
        "NOT VALID WITHOUT SIGNATURE",
        "Academic Status",
        "Full mark is 20",
        "Last Status :",
        "END OF TRANSCRIPT",
        "NOTE:",
        "Indicates that",
        "abbreviations are used:",
        "Emergency Drop",
        "Incomplete",
        "Reported",
        "Not Reported"
    ]

    all_col1 = []
    all_col2 = []

    for page in pages:
        lines = page.split("\n")
        if not lines:
            continue
        for line in lines:
            l_strip = line.strip()
            if not l_strip:
                continue
            if any(kw in l_strip for kw in header_footer_keywords):
                continue
            all_col1.append(line[:76].rstrip())
            all_col2.append(line[76:].rstrip())

    s1 = _parse_column(all_col1)
    s2 = _parse_column(all_col2)

    semesters = []
    max_len = max(len(s1), len(s2))
    for i in range(max_len):
        if i < len(s1):
            semesters.append(s1[i])
        if i < len(s2):
            semesters.append(s2[i])

    # Filter out empty semesters
    semesters = [s for s in semesters if s["courses"]]

    # Calculate cumulative credits and semester numbering
    cum_credits = 0
    regular_sem_idx = 0
    for s in semesters:
        sem_credits = sum(c["credits"] for c in s["courses"])
        cum_credits += sem_credits
        s["semester_credits"] = sem_credits
        s["cumulative_credits"] = cum_credits

        is_summer = "summer" in s["term_name"].lower() or "summer" in s.get("raw_term", "").lower()
        s["is_summer"] = is_summer

        if is_summer:
            s["semester_number"] = None
            # e.g. "Summer Semester: Academic Year 2025–2026"
            year_match = re.search(r"(\d{4}[–\-]\d{4})", s["term_name"])
            year_str = f" ({year_match.group(1)})" if year_match else ""
            s["display_heading"] = f"Summer Semester{year_str}"
            s["divider_title"] = "SUMMER SEMESTER"
            s["divider_subtitle"] = f"Academic Year {year_match.group(1)}" if year_match else s["term_name"]
        else:
            regular_sem_idx += 1
            s["semester_number"] = regular_sem_idx
            s["display_heading"] = f"Semester {regular_sem_idx}: {s['term_name']}"
            s["divider_title"] = f"SEMESTER {regular_sem_idx}"
            s["divider_subtitle"] = s["term_name"]

    return {
        "major": major,
        "degree_level": degree_level,
        "semesters": semesters,
        "regular_semesters_count": regular_sem_idx,
        "total_credits": cum_credits
    }


def _clean_term_name(raw_term):
    """Clean up academic year and semester heading."""
    t = re.sub(r"EXCELLENT.*", "", raw_term).strip()
    t = re.sub(r"Academic Year\s*", "", t).strip()
    # Format e.g. "2023-2024 1st. Semester" -> "Academic Year 2023–2024 (1st Semester)"
    m = re.match(r"^(\d{4}[-/]\d{4})\s*(.*)$", t)
    if m:
        year = m.group(1).replace("/", "–").replace("-", "–")
        term = m.group(2).strip()
        term = term.replace("1st. Semester", "1st Semester")
        term = term.replace("2nd. Semester", "2nd Semester")
        term = term.replace("Summer Semester", "Summer Semester")
        return f"Academic Year {year} ({term})"
    return f"Academic Year {t}"


def _parse_column(col_lines):
    semesters = []
    current_sem = None
    in_courses = False

    for line in col_lines:
        line_str = line.strip()
        if not line_str:
            continue

        if "Academic Year" in line:
            clean_term = _clean_term_name(line_str)
            current_sem = {
                "term_name": clean_term,
                "raw_term": line_str,
                "courses": []
            }
            semesters.append(current_sem)
            in_courses = False
            continue

        if current_sem is None:
            continue

        if "Course Title" in line:
            in_courses = True
            continue

        if ("Semester" in line and "GPA" in line) or "Registered" in line:
            in_courses = False
            continue

        if in_courses:
            # Match course row: <Title> <Credit> <Grade/Status> ...
            # Credits is an integer (1, 2, 3, 4)
            # Grade is float or letters (18.5, NR, IC, R, Pass, Fail, ED, W, P, F)
            m_course = re.match(r"^(.*?)\s{2,}(\d+)\s+([0-9\.]+|NR|IC|Pass|Fail|R|ED|W|P|F)(?:\s+(.*))?$", line.strip())
            if m_course:
                c_title = m_course.group(1).strip()
                credits = int(m_course.group(2))
                grade = m_course.group(3).strip()
                # Skip emergency dropped or withdrawn courses (not completed/earned)
                if grade in ("ED", "W"):
                    continue
                current_sem["courses"].append({
                    "title": c_title,
                    "credits": credits
                })
            else:
                # Multi-line title wrap
                # Ignore noise lines
                if (current_sem["courses"] and
                    not any(kw in line for kw in ["Semester", "Status", "Total", "Unit", "GPA", "NOTE", "Effect", "Academic", "Course Title"])):
                    # Append continuation text
                    extra = line.strip()
                    if extra:
                        current_sem["courses"][-1]["title"] += " " + extra

    return semesters


def match_courses_with_catalog(semesters, catalog=None, aliases=None):
    """
    Match all courses in parsed semesters against the course catalog.
    Annotates each course with:
      - course_id: matched catalog ID or generated slug
      - course_data: full course dict if found, else None
      - is_missing: bool
    Returns:
      annotated_semesters: list of semester dicts
      missing_courses: list of dicts for missing courses
    """
    if catalog is None:
        catalog = load_catalog()
    if aliases is None:
        aliases = load_aliases()

    # Pre-build normalized catalog lookup tables
    by_slug = {}
    by_norm_title = {}
    for cid, c in catalog.items():
        by_slug[cid] = (cid, c)
        t = c.get("title", "")
        by_norm_title[normalize_title(t)] = (cid, c)
        by_norm_title[normalize_title(cid)] = (cid, c)

    # Normalize aliases lookup
    norm_aliases = {normalize_title(k): v for k, v in aliases.items()}

    missing_courses = []

    for sem in semesters:
        for c in sem["courses"]:
            raw_title = c["title"]
            norm_t = normalize_title(raw_title)

            matched_id = None
            matched_data = None

            # 1. Check aliases
            if norm_t in norm_aliases:
                alias_id = norm_aliases[norm_t]
                if alias_id in catalog:
                    matched_id = alias_id
                    matched_data = catalog[alias_id]

            # 2. Check direct title match
            if not matched_id and norm_t in by_norm_title:
                matched_id, matched_data = by_norm_title[norm_t]

            # 3. Check direct slug match
            slug = title_to_slug(raw_title)
            if not matched_id and slug in by_slug:
                matched_id, matched_data = by_slug[slug]

            # 4. Fuzzy title match (threshold >= 0.88)
            if not matched_id:
                best_ratio = 0.0
                best_match = None
                for cat_norm, (cat_id, cat_data) in by_norm_title.items():
                    ratio = SequenceMatcher(None, norm_t, cat_norm).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = (cat_id, cat_data)
                if best_ratio >= 0.88 and best_match:
                    matched_id, matched_data = best_match

            if matched_id and matched_data:
                c["course_id"] = matched_id
                c["course_data"] = matched_data
                c["is_missing"] = False
                c["type"] = matched_data.get("type", "Major | Theoretical")
            else:
                c["course_id"] = slug
                c["course_data"] = None
                c["is_missing"] = True
                c["type"] = "Specialized | Theoretical"
                missing_courses.append({
                    "title": raw_title,
                    "credits": c["credits"],
                    "suggested_id": slug,
                    "term": sem.get("term_name", "")
                })

    return semesters, missing_courses


def generate_course_stub(course_title, credits=3, course_type="Specialized | Theoretical", course_id=None):
    """
    Generate and save a skeleton JSON file for a missing course.
    """
    if not course_id:
        course_id = title_to_slug(course_title)

    stub_path = COURSES_DIR / f"{course_id}.json"
    if stub_path.exists():
        with open(stub_path, "r", encoding="utf-8") as f:
            return json.load(f)

    COURSES_DIR.mkdir(parents=True, exist_ok=True)

    hours = f"{int(credits) * 16}h Theoretical"

    stub_data = {
        "id": course_id,
        "title": course_title,
        "credits": str(credits),
        "type": course_type,
        "prerequisites": None,
        "hours": hours,
        "objectives": f"Comprehensive introduction to the principles, theoretical foundations, and practical techniques of {course_title}.",
        "syllabus": f"- Overview and Foundations of {course_title}\n- Core Theoretical Methodologies and Analytical Models\n- Advanced Topics, Implementations, and Practical Applications",
        "textbooks": f"1. Standard Academic Textbooks and Reference Literature in {course_title}.",
        "layout": "standalone"
    }

    with open(stub_path, "w", encoding="utf-8") as f:
        json.dump(stub_data, f, indent=2, ensure_ascii=False)

    # Also update catalog
    catalog = load_catalog()
    catalog[course_id] = stub_data
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"[Stub Created] Auto-generated course stub: {stub_path}")
    return stub_data
