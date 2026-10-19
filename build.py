#!/usr/bin/env python3
"""
Course Description Builder & Reverse-Engineering Manager
University of Tehran - School of Electrical and Computer Engineering

Allows adding, removing, reordering, and customizing courses and degree programs,
and generating a matching Course Description PDF using XeLaTeX.
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path

import transcript_parser

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
COURSES_DIR = DATA_DIR / "courses"
TEMPLATES_DIR = BASE_DIR / "templates"
ASSETS_DIR = BASE_DIR / "assets"
PROGRAMS_FILE = DATA_DIR / "programs.json"
CATALOG_FILE = DATA_DIR / "courses.json"
MAIN_TEX = BASE_DIR / "main.tex"
DEFAULT_OUTPUT_PDF = BASE_DIR / "CourseDescription.pdf"
COURSE_FILTERS_FILE = DATA_DIR / "course_filters.json"


def load_course_filters():
    """Load configurable filters for religious and general courses."""
    if not COURSE_FILTERS_FILE.exists():
        return {
            "religious_courses": {"course_ids": [], "keywords": []},
            "general_courses": {"course_ids": [], "keywords": []}
        }
    with open(COURSE_FILTERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_religious_course(cid, course_data, title, filters):
    """Check if a course matches religious course filters."""
    rel = filters.get("religious_courses", {})
    if cid and cid in rel.get("course_ids", []):
        return True
    norm_t = (title or "").lower()
    for kw in rel.get("keywords", []):
        if kw.lower() in norm_t:
            return True
    return False


def is_general_course(cid, course_data, title, filters):
    """Check if a course matches general course filters (including religious courses)."""
    if is_religious_course(cid, course_data, title, filters):
        return True
    gen = filters.get("general_courses", {})
    if cid and cid in gen.get("course_ids", []):
        return True
    norm_t = (title or "").lower()
    for kw in gen.get("keywords", []):
        if kw.lower() in norm_t:
            return True
    ctype = (course_data.get("type", "") if course_data else "").lower()
    if "general" in ctype:
        return True
    return False


def get_category_rank(course_type):
    """Return numeric rank for category ordering."""
    ct = (course_type or "").lower()
    if "basic" in ct:
        return 1
    if "major" in ct:
        return 2
    if "specialized" in ct:
        return 3
    if "elective" in ct:
        return 4
    if "general" in ct:
        return 5
    if "workshop" in ct:
        return 6
    if "internship" in ct or "training" in ct:
        return 7
    if "project" in ct:
        return 8
    return 9


def find_latex_compiler():
    """Locate xelatex (preferred for unicode & Liberation/Times fonts) or pdflatex."""
    candidates = [
        "/home/manih/.TinyTeX/bin/x86_64-linux/xelatex",
        shutil.which("xelatex"),
        "/home/manih/.TinyTeX/bin/x86_64-linux/pdflatex",
        shutil.which("pdflatex")
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return "xelatex"


def escape_latex(text):
    """Escape special LaTeX characters safely."""
    if not text:
        return ""
    # Characters that need escaping in regular text
    replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
    ]
    s = str(text)
    for orig, rep in replacements:
        # Avoid double escaping
        s = s.replace(rep, orig)
        s = s.replace(orig, rep)
    return s


def load_programs():
    if not PROGRAMS_FILE.exists():
        raise FileNotFoundError(f"Missing {PROGRAMS_FILE}")
    with open(PROGRAMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_programs(data):
    with open(PROGRAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_course(course_id):
    course_path = COURSES_DIR / f"{course_id}.json"
    if not course_path.exists():
        # Fallback to catalog
        if CATALOG_FILE.exists():
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                catalog = json.load(f)
                if course_id in catalog:
                    return catalog[course_id]
        raise FileNotFoundError(f"Course file not found: {course_path}")
    with open(course_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_course(course_dict):
    cid = course_dict["id"]
    course_path = COURSES_DIR / f"{cid}.json"
    with open(course_path, "w", encoding="utf-8") as f:
        json.dump(course_dict, f, indent=2, ensure_ascii=False)
    # Update catalog
    catalog = {}
    if CATALOG_FILE.exists():
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    catalog[cid] = course_dict
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)


def format_course_latex(course, is_first_compact=False):
    """Format a single course into LaTeX."""
    lines = []
    layout = course.get("layout", "standalone")

    if layout == "standalone":
        lines.append(r"\newpage")
    else:
        if is_first_compact:
            lines.append(r"\newpage")
        else:
            lines.append(r"\par\vspace{14pt}")
        lines.append(r"\nopagebreak")

    lines.append(f"\\textbf{{Title of the Course:}} {escape_latex(course['title'])}\\\\")
    lines.append(f"\\textbf{{Number of Credits:}} {escape_latex(course['credits'])}\\\\")
    lines.append(f"\\textbf{{Type of the Course:}} {escape_latex(course['type'])}\\\\")

    if course.get("prerequisites"):
        lines.append(f"\\textbf{{Pre-requisite:}} {escape_latex(course['prerequisites'])}\\\\")

    lines.append(f"\\textbf{{Training hours:}} {escape_latex(course['hours'])}\\par\\vspace{{4pt}}")

    if course.get("objectives"):
        lines.append(r"\textbf{Course Objectives:}\par\vspace{2pt}")
        lines.append(escape_latex(course["objectives"]) + r"\par\vspace{4pt}")

    if course.get("syllabus"):
        lines.append(r"\textbf{Syllabus of Courses:}\par\vspace{2pt}")
        syl_lines = course["syllabus"].split("\n")
        formatted_syl = []
        for sl in syl_lines:
            sl_str = sl.strip()
            if not sl_str:
                continue
            if sl_str.startswith("- "):
                formatted_syl.append(r"\vspace{2pt}\textbf{" + escape_latex(sl_str) + r"}\par")
            else:
                formatted_syl.append(escape_latex(sl_str) + r"\par")
        lines.append("\n".join(formatted_syl) + r"\vspace{4pt}")

    if course.get("textbooks"):
        lines.append(r"\textbf{TextBooks:}\par\vspace{2pt}")
        tb_lines = course["textbooks"].split("\n")
        for tbl in tb_lines:
            tbl_str = tbl.strip()
            if tbl_str:
                lines.append(escape_latex(tbl_str) + r"\par")
        lines.append(r"\vspace{4pt}")

    return "\n".join(lines)


def generate_latex(program_id=None, selected_course_ids=None, semesters_data=None, missing_courses=None,
                   style="semester", omit_general=False, omit_religion=False, major=None):
    """Generate main.tex from templates/template.tex and course data."""
    config = load_programs()
    inst = config["institution"]

    if not program_id:
        if major == "ee":
            program_id = "electrical_engineering_bsc"
        else:
            program_id = config.get("default_program", "computer_engineering_bsc")

    if program_id not in config["programs"]:
        raise ValueError(f"Unknown program '{program_id}'. Available: {list(config['programs'].keys())}")

    prog = dict(config["programs"][program_id])

    # If major is explicitly set, adjust program display name
    if major == "ee":
        prog["program_name"] = "Electrical Engineering"
    elif major == "ce":
        prog["program_name"] = "Computer Engineering"

    curriculum_overview = ""
    courses_tex_blocks = []
    filters = load_course_filters()

    if semesters_data:
        # Pre-process courses for omission and missing status
        has_omitted_courses = False
        has_missing_courses = False

        for sem in semesters_data:
            for c in sem["courses"]:
                cid = c.get("course_id")
                cdata = c.get("course_data")
                ctitle = c.get("title", "")

                is_omitted = False
                if omit_religion and is_religious_course(cid, cdata, ctitle, filters):
                    is_omitted = True
                elif omit_general and is_general_course(cid, cdata, ctitle, filters):
                    is_omitted = True

                c["is_omitted"] = is_omitted
                if is_omitted:
                    has_omitted_courses = True
                if c.get("is_missing"):
                    has_missing_courses = True

        # 1. Format Curriculum Overview table
        ov_lines = [
            r"\textbf{\LARGE Curriculum Overview: Semester-by-Semester Study Plan}\par\vspace{6pt}",
            r"The following study plan outlines the curriculum courses undertaken across all academic semesters, including course categories and credit allocations. This document provides official course descriptions and syllabi for all included courses.\par\vspace{10pt}"
        ]

        for sem in semesters_data:
            heading = sem.get("display_heading") or f"Semester {sem.get('semester_number', '')}: {sem.get('term_name', '')}"
            ov_lines.append(r"\noindent{\large\textbf{" + escape_latex(heading) + r"}}\par\vspace{4pt}")
            ov_lines.append(r"\noindent\begin{tabularx}{\textwidth}{@{} X l r @{}}")
            ov_lines.append(r"\toprule")
            ov_lines.append(r"\textbf{Course Title} & \textbf{Course Type} & \textbf{Credits} \\")
            ov_lines.append(r"\midrule")
            for c in sem["courses"]:
                c_title = escape_latex(c["title"])
                if c.get("is_missing"):
                    c_title += r" \textit{\textcolor{red!75!black}{(Not Included in Syllabus)}}"
                elif c.get("is_omitted"):
                    c_title += r" \textit{\textcolor{gray!80!black}{(Omitted from Syllabus)}}"
                c_type = escape_latex(c.get("type", "Specialized | Theoretical"))
                c_credits = escape_latex(str(c.get("credits", "3")))
                ov_lines.append(f"{c_title} & {c_type} & {c_credits} \\\\")
            ov_lines.append(r"\midrule")
            ov_lines.append(f"\\multicolumn{{2}}{{@{{}}l}}{{\\textbf{{Total Semester Credits: {sem['semester_credits']}}}}} & \\textbf{{Cumulative: {sem['cumulative_credits']}}} \\\\")
            ov_lines.append(r"\bottomrule")
            ov_lines.append(r"\end{tabularx}\par\vspace{14pt}")

        if has_missing_courses:
            ov_lines.append(r"\vspace{3pt}\noindent\textit{\textcolor{red!75!black}{* Courses marked (Not Included in Syllabus) are present in the academic transcript but not currently archived in the course catalogue.}}\par")
        if has_omitted_courses:
            ov_lines.append(r"\vspace{2pt}\noindent\textit{\textcolor{gray!80!black}{* Courses marked (Omitted from Syllabus) are general/non-engineering offerings omitted from this syllabus document.}}\par")

        ov_lines.append(r"\newpage")
        curriculum_overview = "\n".join(ov_lines)

        # 2. Format detailed course descriptions
        seen_courses = set()

        if style == "semester":
            # Semester-by-semester with dedicated divider pages
            for sem in semesters_data:
                term_courses = []
                for c in sem["courses"]:
                    if c.get("is_missing") or c.get("is_omitted"):
                        continue
                    cid = c.get("course_id")
                    if cid and cid in seen_courses:
                        continue
                    term_courses.append(c)

                if not term_courses:
                    continue

                div_title = sem.get("divider_title") or f"SEMESTER {sem.get('semester_number', '')}"
                div_subtitle = sem.get("divider_subtitle") or sem.get("term_name", "")

                courses_tex_blocks.append(
                    r"\newpage" + "\n" +
                    r"\vspace*{\fill}" + "\n" +
                    r"\begin{center}" + "\n" +
                    r"  {\fontsize{28pt}{34pt}\selectfont \textbf{" + escape_latex(div_title) + r"}}\par\vspace{12pt}" + "\n" +
                    r"  {\fontsize{13pt}{17pt}\selectfont " + escape_latex(div_subtitle) + r"}" + "\n" +
                    r"\end{center}" + "\n" +
                    r"\vspace*{\fill}"
                )

                in_compact = False
                for c in term_courses:
                    cid = c.get("course_id")
                    if cid:
                        seen_courses.add(cid)
                    course_obj = c.get("course_data")
                    if not course_obj and cid:
                        try:
                            course_obj = load_course(cid)
                        except Exception:
                            pass
                    if not course_obj:
                        continue

                    is_first_compact = False
                    if course_obj.get("layout") == "compact" and not in_compact:
                        in_compact = True
                        is_first_compact = True
                    elif course_obj.get("layout") == "standalone":
                        in_compact = False

                    courses_tex_blocks.append(format_course_latex(course_obj, is_first_compact))

        else:
            # style == "category": Basic -> Major -> Specialized -> Elective -> General -> Workshop -> Internship -> Project
            all_valid_courses = []
            for sem in semesters_data:
                for c in sem["courses"]:
                    if c.get("is_missing") or c.get("is_omitted"):
                        continue
                    cid = c.get("course_id")
                    if cid and cid in seen_courses:
                        continue
                    if cid:
                        seen_courses.add(cid)
                    course_obj = c.get("course_data")
                    if not course_obj and cid:
                        try:
                            course_obj = load_course(cid)
                        except Exception:
                            pass
                    if not course_obj:
                        continue
                    all_valid_courses.append((course_obj, c))

            prog_course_order = {cid: idx for idx, cid in enumerate(prog.get("courses", []))}
            all_valid_courses.sort(
                key=lambda item: (
                    get_category_rank(item[0].get("type", "")),
                    prog_course_order.get(item[0]["id"], 999),
                    item[0].get("title", "")
                )
            )

            in_compact = False
            for course_obj, c in all_valid_courses:
                is_first_compact = False
                if course_obj.get("layout") == "compact" and not in_compact:
                    in_compact = True
                    is_first_compact = True
                elif course_obj.get("layout") == "standalone":
                    in_compact = False

                courses_tex_blocks.append(format_course_latex(course_obj, is_first_compact))

    else:
        # Standard program or selected courses build
        if selected_course_ids:
            course_ids = selected_course_ids
        else:
            course_ids = prog.get("courses", [])

        in_compact = False
        for cid in course_ids:
            try:
                c = load_course(cid)
            except Exception as e:
                print(f"[Warning] Could not load course '{cid}': {e}", file=sys.stderr)
                continue

            if omit_religion and is_religious_course(cid, c, c.get("title", ""), filters):
                continue
            if omit_general and is_general_course(cid, c, c.get("title", ""), filters):
                continue

            is_first_compact = False
            if c.get("layout") == "compact" and not in_compact:
                in_compact = True
                is_first_compact = True
            elif c.get("layout") == "standalone":
                in_compact = False

            courses_tex_blocks.append(format_course_latex(c, is_first_compact))

    courses_body = "\n\n".join(courses_tex_blocks)

    # Format Remarks
    remarks = prog.get("remarks", {})
    course_types = remarks.get("course_types", [
        "Basic", "Major", "Specialized", "Elective", "General", "Workshop", "Internship", "Project"
    ])
    course_types_enum = "\n  ".join([f"\\item {escape_latex(ct)}" for ct in course_types])
    ministry_stmt = escape_latex(remarks.get("ministry_statement", ""))
    grading_stmt = escape_latex(remarks.get("grading_statement", ""))

    # Load template
    template_path = TEMPLATES_DIR / "template.tex"
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # Fill template variables
    rendered = template_content
    rendered = rendered.replace("UNIVERSITY_NAME", escape_latex(inst.get("university", "University of Tehran")))
    rendered = rendered.replace("CITY_NAME", escape_latex(inst.get("city", "Tehran")))
    rendered = rendered.replace("SCHOOL_NAME", escape_latex(inst.get("school", "School of Electrical and Computer Engineering")))
    rendered = rendered.replace("DOCUMENT_TITLE", escape_latex(inst.get("document_title", "Course Description")))
    rendered = rendered.replace("PROGRAM_NAME", escape_latex(prog.get("program_name", "Computer Engineering")))
    rendered = rendered.replace("DEGREE_NAME", escape_latex(prog.get("degree", "Bachelor’s Degree")))
    rendered = rendered.replace("COURSE_TYPES_ENUMERATE", course_types_enum)
    rendered = rendered.replace("MINISTRY_STATEMENT", ministry_stmt)
    rendered = rendered.replace("GRADING_STATEMENT", grading_stmt)
    rendered = rendered.replace("CURRICULUM_OVERVIEW", curriculum_overview)
    rendered = rendered.replace("COURSES_BODY", courses_body)

    with open(MAIN_TEX, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"Generated {MAIN_TEX} with {len(courses_tex_blocks)} courses.")
    return MAIN_TEX


def compile_pdf(tex_file=MAIN_TEX, output_pdf=DEFAULT_OUTPUT_PDF):
    """Compile LaTeX to PDF using XeLaTeX (2 passes)."""
    compiler = find_latex_compiler()
    print(f"Compiling with: {compiler} (Target: {output_pdf.name})...")

    # Pass 1
    res1 = subprocess.run(
        [compiler, "-interaction=nonstopmode", tex_file.name],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    if res1.returncode != 0:
        log_file = BASE_DIR / f"{tex_file.stem}.log"
        print(f"[Error] Compilation failed! Check log: {log_file}", file=sys.stderr)
        with open(log_file, "r", encoding="utf-8", errors="replace") as lf:
            lines = [l.strip() for l in lf.readlines() if l.startswith("!")]
            for l in lines[:10]:
                print(f"  {l}", file=sys.stderr)
        return False

    # Pass 2 for cross references & pagination
    subprocess.run(
        [compiler, "-interaction=nonstopmode", tex_file.name],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    built_pdf = BASE_DIR / f"{tex_file.stem}.pdf"
    if built_pdf.exists():
        if built_pdf.resolve() != output_pdf.resolve():
            shutil.copy2(built_pdf, output_pdf)
            built_pdf.unlink()
        print(f"Successfully compiled PDF: {output_pdf}")
        return True
    return False


def clean_artifacts():
    """Remove LaTeX auxiliary files."""
    exts = [".aux", ".log", ".out", ".toc", ".synctex.gz", ".fdb_latexmk", ".fls"]
    removed = 0
    for ext in exts:
        for f in BASE_DIR.glob(f"*{ext}"):
            f.unlink()
            removed += 1
    print(f"Cleaned {removed} auxiliary build files.")


def list_programs():
    config = load_programs()
    print("\nAvailable Programs:")
    default_p = config.get("default_program")
    for pid, p in config["programs"].items():
        is_def = " (DEFAULT)" if pid == default_p else ""
        num_courses = len(p.get("courses", []))
        print(f"  • {pid}{is_def}: {p.get('program_name')} ({p.get('degree')}) - {num_courses} courses")
    print()


def list_courses(program_id=None):
    config = load_programs()
    if program_id:
        if program_id not in config["programs"]:
            print(f"Program '{program_id}' not found.")
            return
        cids = config["programs"][program_id].get("courses", [])
        title = f"Courses in program '{program_id}' ({len(cids)} total):"
    else:
        # All available courses in catalog
        if CATALOG_FILE.exists():
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                catalog = json.load(f)
            cids = list(catalog.keys())
        else:
            cids = [f.stem for f in COURSES_DIR.glob("*.json")]
        title = f"All available courses in catalog ({len(cids)} total):"

    print(f"\n{title}")
    total_credits = 0
    for idx, cid in enumerate(cids, 1):
        try:
            c = load_course(cid)
            credits = c.get("credits", "?")
            try:
                total_credits += int(credits)
            except ValueError:
                pass
            ctype = c.get("type", "Unknown")
            print(f"  {idx:2d}. [{cid}] {c.get('title')} ({credits} cr, {ctype})")
        except Exception:
            print(f"  {idx:2d}. [{cid}] (Failed to load details)")
    print(f"Total credits: {total_credits}\n")


def add_course_cli(args):
    """Scaffold or add a course."""
    cid = args.id
    if not cid:
        cid = input("Course ID / slug (e.g. machine_learning): ").strip()
    if not cid:
        print("Course ID is required.")
        return

    title = args.title or input("Course Title: ").strip()
    credits = args.credits or input("Number of credits (e.g. 3): ").strip()
    ctype = args.type or input("Type of Course (e.g. Specialized | Theoretical): ").strip()
    hours = args.hours or input("Training hours (e.g. 48h Theoretical): ").strip()
    prereq = args.prereq
    if prereq is None:
        p_in = input("Pre-requisite (leave empty if none): ").strip()
        prereq = p_in if p_in else None
    objectives = args.objectives or input("Course Objectives (paragraph): ").strip()

    course_data = {
        "id": cid,
        "title": title,
        "credits": str(credits),
        "type": ctype,
        "prerequisites": prereq,
        "hours": hours,
        "objectives": objectives,
        "syllabus": args.syllabus,
        "textbooks": args.textbooks,
        "layout": args.layout or "standalone"
    }

    save_course(course_data)
    print(f"Saved course '{cid}' to {COURSES_DIR / f'{cid}.json'}")

    # Add to program if specified
    config = load_programs()
    prog_id = args.program or config.get("default_program")
    if prog_id in config["programs"]:
        prog_courses = config["programs"][prog_id].setdefault("courses", [])
        if cid not in prog_courses:
            prog_courses.append(cid)
            save_programs(config)
            print(f"Added course '{cid}' to program '{prog_id}'.")


def remove_course_cli(args):
    """Remove a course from a program."""
    cid = args.remove_course
    config = load_programs()
    prog_id = args.program or config.get("default_program")
    if prog_id not in config["programs"]:
        print(f"Program '{prog_id}' not found.")
        return
    prog_courses = config["programs"][prog_id].get("courses", [])
    if cid in prog_courses:
        prog_courses.remove(cid)
        save_programs(config)
        print(f"Removed course '{cid}' from program '{prog_id}'.")
    else:
        print(f"Course '{cid}' is not in program '{prog_id}'.")


def add_program_cli(args):
    """Create a new program definition."""
    pid = args.add_program
    config = load_programs()
    if pid in config["programs"]:
        print(f"Program '{pid}' already exists.")
        return

    name = args.name or input("Program name (e.g. Computer Science): ").strip()
    degree = args.degree or input("Degree (e.g. Master's Degree): ").strip()

    config["programs"][pid] = {
        "program_name": name,
        "degree": degree,
        "degree_type": "master" if "master" in degree.lower() else "bachelor",
        "remarks": config["programs"]["computer_engineering_bsc"]["remarks"],
        "courses": []
    }
    save_programs(config)
    print(f"Created new program '{pid}'. Add courses using --add-course or editing data/programs.json.")


def main():
    parser = argparse.ArgumentParser(description="Course Description PDF Generator & Manager")
    parser.add_argument("--transcript", "-t", help="Path to transcript PDF or text file to generate personalized course descriptions")
    parser.add_argument("--style", choices=["semester", "category"], help="Document style: 'semester' (chronological with divider pages) or 'category' (grouped by course classification)")
    parser.add_argument("--omit-general", action="store_true", help="Omit general courses from course description pages")
    parser.add_argument("--omit-religion", action="store_true", help="Omit religious courses from course description pages")
    parser.add_argument("--major", choices=["ce", "ee"], type=str.lower, help="Major: 'ce' (Computer Engineering) or 'ee' (Electrical Engineering)")
    parser.add_argument("--program", "-p", help="Target program ID (e.g. computer_engineering_bsc)")
    parser.add_argument("--courses", "-c", nargs="+", help="Specific course IDs to include in order")
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT_PDF), help="Output PDF path")
    parser.add_argument("--no-pdf", action="store_true", help="Generate main.tex only without compiling PDF")
    parser.add_argument("--clean", action="store_true", help="Clean auxiliary files")
    parser.add_argument("--list-programs", action="store_true", help="List all defined programs")
    parser.add_argument("--list-courses", action="store_true", help="List all courses")
    parser.add_argument("--add-course", action="store_true", help="Add or scaffold a new course")
    parser.add_argument("--remove-course", help="Remove a course ID from the target program")
    parser.add_argument("--add-program", help="Add a new program with given ID")

    # Options for adding course
    parser.add_argument("--id", help="Course slug ID")
    parser.add_argument("--title", help="Course title")
    parser.add_argument("--credits", help="Credit count")
    parser.add_argument("--type", help="Course type")
    parser.add_argument("--hours", help="Training hours")
    parser.add_argument("--prereq", help="Course prerequisites")
    parser.add_argument("--objectives", help="Course objectives")
    parser.add_argument("--syllabus", help="Course syllabus")
    parser.add_argument("--textbooks", help="Course textbooks")
    parser.add_argument("--layout", choices=["standalone", "compact"], help="Layout style")
    parser.add_argument("--name", help="Program display name (for --add-program)")
    parser.add_argument("--degree", help="Degree name (for --add-program)")

    args = parser.parse_args()

    if args.clean:
        clean_artifacts()
        return

    if args.list_programs:
        list_programs()
        return

    if args.list_courses:
        list_courses(args.program)
        return

    if args.add_program:
        add_program_cli(args)
        return

    if args.remove_course:
        remove_course_cli(args)
        return

    if args.add_course:
        add_course_cli(args)
        return

    # Transcript-based build
    if args.transcript:
        t_path = Path(args.transcript)
        if not t_path.exists():
            print(f"[Error] Transcript file not found: {t_path}", file=sys.stderr)
            sys.exit(1)

        print("\n=======================================================")
        print(f" Parsing Transcript: {t_path.name}")
        print("=======================================================\n")

        res = transcript_parser.parse_transcript(t_path)
        print(f"  • Major: {res['major']}")
        print(f"  • Degree Level: {res['degree_level']}")
        print(f"  • Regular Semesters: {res['regular_semesters_count']}")
        print(f"  • Total Semesters: {len(res['semesters'])}")
        print(f"  • Total Registered / Passed Credits: {res['total_credits']}\n")

        semesters, missing = transcript_parser.match_courses_with_catalog(res["semesters"])

        if missing:
            print(f"⚠️  [NOTICE] You are missing the following {len(missing)} course(s) from the catalogue:")
            for m in missing:
                print(f"   • {m['title']} ({m['credits']} cr) [{m['term']}]")
            print(f"\nProceeding to generate course description with {len(missing)} missing course(s) skipped.\n")
        else:
            total_courses = sum(len(s['courses']) for s in semesters)
            print(f"✓ All {total_courses} courses matched against the catalog!\n")

        chosen_style = args.style if args.style else "semester"

        # Determine major (CLI override or auto-detected)
        major = args.major
        if not major:
            detected = (res.get("major") or "").lower()
            if "electrical" in detected:
                major = "ee"
            else:
                major = "ce"

        target_prog = args.program
        if not target_prog:
            target_prog = "electrical_engineering_bsc" if major == "ee" else "computer_engineering_bsc"

        tex_path = generate_latex(
            program_id=target_prog,
            semesters_data=semesters,
            missing_courses=missing,
            style=chosen_style,
            omit_general=args.omit_general,
            omit_religion=args.omit_religion,
            major=major
        )
    else:
        # Default action: Generate standard program or selected course list
        chosen_style = args.style if args.style else "category"

        major = args.major or "ce"
        target_prog = args.program
        if not target_prog:
            target_prog = "electrical_engineering_bsc" if major == "ee" else "computer_engineering_bsc"

        tex_path = generate_latex(
            program_id=target_prog,
            selected_course_ids=args.courses,
            style=chosen_style,
            omit_general=args.omit_general,
            omit_religion=args.omit_religion,
            major=major
        )

    if not args.no_pdf:
        success = compile_pdf(tex_file=tex_path, output_pdf=Path(args.output))
        if success:
            clean_artifacts()
            print(f"\n[DONE] Course Description PDF is ready at: {args.output}\n")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
