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

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
COURSES_DIR = DATA_DIR / "courses"
TEMPLATES_DIR = BASE_DIR / "templates"
ASSETS_DIR = BASE_DIR / "assets"
PROGRAMS_FILE = DATA_DIR / "programs.json"
CATALOG_FILE = DATA_DIR / "courses.json"
MAIN_TEX = BASE_DIR / "main.tex"
DEFAULT_OUTPUT_PDF = BASE_DIR / "CourseDescription.pdf"


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


def generate_latex(program_id=None, selected_course_ids=None):
    """Generate main.tex from templates/template.tex and course data."""
    config = load_programs()
    inst = config["institution"]

    if not program_id:
        program_id = config.get("default_program", "computer_engineering_bsc")

    if program_id not in config["programs"]:
        raise ValueError(f"Unknown program '{program_id}'. Available: {list(config['programs'].keys())}")

    prog = config["programs"][program_id]

    if selected_course_ids:
        course_ids = selected_course_ids
    else:
        course_ids = prog.get("courses", [])

    # Format courses body
    courses_tex_blocks = []
    in_compact = False
    for cid in course_ids:
        try:
            c = load_course(cid)
        except Exception as e:
            print(f"[Warning] Could not load course '{cid}': {e}", file=sys.stderr)
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

    # Default action: Generate and compile
    tex_path = generate_latex(program_id=args.program, selected_course_ids=args.courses)

    if not args.no_pdf:
        success = compile_pdf(tex_file=tex_path, output_pdf=Path(args.output))
        if success:
            clean_artifacts()
            print(f"\n[DONE] Course Description PDF is ready at: {args.output}\n")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
