#!/usr/bin/env python3
"""
Transcript Test Runner & Verification Suite
University of Tehran — School of Electrical and Computer Engineering

Runs automated verification on test transcripts:
1. Parses student transcripts using transcript_parser.py
2. Matches extracted courses against the course catalog (data/courses.json)
3. Detects missing courses, layout discrepancies, or parsing regressions
4. Exports structured summary.json answers per test for manual checking
5. Generates main.tex and CourseDescription.pdf inside each student test folder
6. Compiles a comprehensive markdown test report (tests/test_report.md)
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

import transcript_parser
import build

BASE_DIR = Path(__file__).resolve().parent
TESTS_DIR = BASE_DIR / "tests"
DEFAULT_REPORT_FILE = TESTS_DIR / "test_report.md"

# ANSI Terminal Colors
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def clean_student_artifacts(student_dir: Path):
    """Remove generated test artifacts from a student folder."""
    files_to_remove = ["summary.json", "main.tex", "CourseDescription.pdf"]
    latex_exts = [".aux", ".log", ".out", ".toc", ".synctex.gz", ".fdb_latexmk", ".fls", ".xdv"]
    
    for fname in files_to_remove:
        f = student_dir / fname
        if f.exists():
            f.unlink()
            
    for ext in latex_exts:
        for f in student_dir.glob(f"*{ext}"):
            f.unlink()


def find_test_directories(tests_dir: Path, requested_names=None):
    """
    Find all test folders inside tests/.
    Each folder containing a transcript PDF is considered a test case.
    """
    if not tests_dir.exists():
        return []

    test_dirs = []
    # Find all subdirectories
    for d in sorted(tests_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue

        # Check if requested
        if requested_names:
            normalized_req = [r.strip().lower().replace("-", "_") for r in requested_names]
            if d.name.lower().replace("-", "_") not in normalized_req:
                continue

        # Look for transcript PDF
        pdf_path = d / "transcript.pdf"
        if not pdf_path.exists():
            # Check for any PDF in directory
            pdfs = list(d.glob("*.pdf"))
            # Exclude CourseDescription.pdf if present
            candidates = [p for p in pdfs if p.name.lower() != "coursedescription.pdf"]
            if candidates:
                pdf_path = candidates[0]
            else:
                continue

        test_dirs.append((d, pdf_path))

    return test_dirs


def auto_select_final_courses(semesters, total_credits, target_prog="computer_engineering_bsc"):
    """
    Automatically select a valid set of untaken curriculum courses to reach 140-142 total credits
    for simulated graduation testing.
    Rules:
    1. Project (3 cr) is mandatory if not already taken.
    2. Prefer untaken practical laboratories & workshops.
    3. Fill remaining credits with untaken theory & elective courses.
    4. Exclude industrial_training (0 graduation credit impact).
    5. Term credits must be <= 24 and total credits must fall in [140, 142].
    """
    catalog = transcript_parser.load_catalog()
    config = build.load_programs()
    prog_courses = config.get("programs", {}).get(target_prog, {}).get("courses", [])

    taken_ids = set()
    for s in semesters:
        for c in s.get("courses", []):
            cid = c.get("course_id")
            if cid:
                taken_ids.add(cid)

    needed_credits = 140 - total_credits
    if needed_credits <= 0 or needed_credits > 24:
        return None

    selected = []
    current_cr = 0

    # 1. Mandatory capstone: B.Sc. Project
    if "project" not in taken_ids and "project" in catalog:
        selected.append("project")
        current_cr += int(catalog["project"].get("credits", 3))

    # 2. Practical Laboratories & Workshops
    for cid in prog_courses:
        if cid in taken_ids or cid in selected or cid in ("project", "industrial_training"):
            continue
        c = catalog.get(cid)
        if not c:
            continue
        cr = int(c.get("credits", 0))
        ctype = (c.get("type") or "").lower()
        ctitle = (c.get("title") or "").lower()
        if "practical" in ctype or "laboratory" in ctitle or "workshop" in ctype:
            if current_cr + cr <= 24 and total_credits + current_cr + cr <= 142:
                selected.append(cid)
                current_cr += cr

    # 3. Core & Elective Theory courses
    for cid in prog_courses:
        if cid in taken_ids or cid in selected or cid in ("project", "industrial_training"):
            continue
        c = catalog.get(cid)
        if not c:
            continue
        cr = int(c.get("credits", 0))
        if current_cr + cr <= 24 and total_credits + current_cr + cr <= 142:
            selected.append(cid)
            current_cr += cr
            if total_credits + current_cr >= 140:
                break

    if 140 <= total_credits + current_cr <= 142 and current_cr <= 24:
        return selected
    return None


def run_single_test(student_dir: Path, transcript_pdf: Path, no_pdf: bool = False,
                    style: str = "semester", omit_general: bool = False, omit_religion: bool = False,
                    simulate_graduation: bool = False):
    """
    Run parsing, validation, and PDF generation for a single student transcript.
    Returns result dictionary.
    """
    test_name = student_dir.name
    res_dict = {
        "test_name": test_name,
        "student_folder": str(student_dir.relative_to(BASE_DIR)),
        "transcript_file": str(transcript_pdf.relative_to(BASE_DIR)),
        "timestamp": datetime.now().isoformat(),
        "status": "PASS",
        "error_message": None,
        "major": None,
        "degree_level": None,
        "regular_semesters_count": 0,
        "total_semesters": 0,
        "total_credits": 0,
        "total_courses": 0,
        "missing_courses_count": 0,
        "missing_courses": [],
        "graduating_simulated": False,
        "graduating_courses": [],
        "graduating_note": None,
        "pdf_compiled": False,
        "pdf_path": None,
        "semesters": []
    }

    try:
        # 1. Parse transcript layout
        parse_res = transcript_parser.parse_transcript(transcript_pdf)
        res_dict["major"] = parse_res.get("major", "Computer Engineering")
        res_dict["degree_level"] = parse_res.get("degree_level", "Bachelor")
        res_dict["regular_semesters_count"] = parse_res.get("regular_semesters_count", 0)
        res_dict["total_semesters"] = len(parse_res.get("semesters", []))
        res_dict["total_credits"] = parse_res.get("total_credits", 0)

        # 2. Match with course catalog
        semesters, missing = transcript_parser.match_courses_with_catalog(parse_res["semesters"])
        total_courses = sum(len(s["courses"]) for s in semesters)
        res_dict["total_courses"] = total_courses
        res_dict["missing_courses_count"] = len(missing)
        res_dict["missing_courses"] = missing

        # Determine major and program
        detected_major = (res_dict["major"] or "").lower()
        major = "ee" if "electrical" in detected_major else "ce"
        program_id = "electrical_engineering_bsc" if major == "ee" else "computer_engineering_bsc"

        # 2b. Optional Graduation Simulation
        if simulate_graduation:
            rem = 140 - res_dict["total_credits"]
            if 0 < rem <= 24:
                planned = auto_select_final_courses(semesters, res_dict["total_credits"], program_id)
                if planned:
                    semesters, added = build.plan_final_semester(
                        semesters=semesters,
                        res=parse_res,
                        target_prog=program_id,
                        no_prompt=True,
                        cli_future_courses=planned
                    )
                    if added:
                        res_dict["graduating_simulated"] = True
                        res_dict["graduating_courses"] = planned
                        res_dict["total_credits"] = parse_res.get("total_credits", res_dict["total_credits"])
                        res_dict["regular_semesters_count"] = parse_res.get("regular_semesters_count", res_dict["regular_semesters_count"])
                        res_dict["total_semesters"] = len(semesters)
                        res_dict["total_courses"] = sum(len(s["courses"]) for s in semesters)
            else:
                res_dict["graduating_simulated"] = False
                res_dict["graduating_note"] = f"Remaining credits ({rem} cr) outside next-semester window (<= 24 cr)."

        # Serialize semesters for inspection (clean dicts without non-serializable objects)
        serialized_semesters = []
        for sem in semesters:
            sem_entry = {
                "term_name": sem.get("term_name", ""),
                "display_heading": sem.get("display_heading", ""),
                "semester_number": sem.get("semester_number"),
                "is_summer": sem.get("is_summer", False),
                "semester_credits": sem.get("semester_credits", 0),
                "cumulative_credits": sem.get("cumulative_credits", 0),
                "courses_count": len(sem.get("courses", [])),
                "courses": [
                    {
                        "title": c.get("title", ""),
                        "credits": c.get("credits", 0),
                        "course_id": c.get("course_id", ""),
                        "is_missing": c.get("is_missing", False),
                        "type": c.get("type", "")
                    }
                    for c in sem.get("courses", [])
                ]
            }
            serialized_semesters.append(sem_entry)
        res_dict["semesters"] = serialized_semesters

        if missing:
            res_dict["status"] = "WARNING"
        else:
            res_dict["status"] = "PASS"

        # 3. Save summary.json in the test folder for manual/automated inspection
        summary_path = student_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(res_dict, f, indent=2, ensure_ascii=False)

        # Determine major and program
        detected_major = (res_dict["major"] or "").lower()
        major = "ee" if "electrical" in detected_major else "ce"
        program_id = "electrical_engineering_bsc" if major == "ee" else "computer_engineering_bsc"

        # Generate LaTeX
        tex_file = build.generate_latex(
            program_id=program_id,
            semesters_data=semesters,
            missing_courses=missing,
            style=style,
            omit_general=omit_general,
            omit_religion=omit_religion,
            major=major
        )

        # Copy main.tex to test directory
        dest_tex = student_dir / "main.tex"
        shutil.copy2(tex_file, dest_tex)

        # 4. Compile PDF (unless --no-pdf)
        if not no_pdf:
            dest_pdf = student_dir / "CourseDescription.pdf"
            compile_success = build.compile_pdf(tex_file=tex_file, output_pdf=dest_pdf)
            build.clean_artifacts()

            if compile_success and dest_pdf.exists():
                res_dict["pdf_compiled"] = True
                res_dict["pdf_path"] = str(dest_pdf.relative_to(BASE_DIR))
            else:
                res_dict["status"] = "FAIL"
                res_dict["error_message"] = "PDF compilation failed."

            # Update summary.json with final PDF status
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(res_dict, f, indent=2, ensure_ascii=False)

    except Exception as e:
        res_dict["status"] = "FAIL"
        res_dict["error_message"] = str(e)
        summary_path = student_dir / "summary.json"
        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(res_dict, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return res_dict


def render_terminal_table(results: list, no_pdf: bool, simulate_graduation: bool = False):
    """Print an aesthetic, color-coded summary table in the terminal."""
    headers = ["Test Name", "Major", "Semesters", "Courses", "Credits", "Missing Courses", "PDF", "Status"]
    col_widths = [16, 8, 11, 9, 13, 28, 12, 10]

    def truncate(s, length):
        s = str(s)
        return s[:length - 2] + ".." if len(s) > length else s

    sep_line = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_line = "|" + "|".join(f" {h.center(w)} " for h, w in zip(headers, col_widths)) + "|"

    print("\n" + sep_line)
    print(header_line)
    print(sep_line)

    for r in results:
        name = truncate(r["test_name"], col_widths[0])
        major = "EE" if "electrical" in (r["major"] or "").lower() else "CE"
        semesters = f"{r['total_semesters']} ({r['regular_semesters_count']} reg)"
        courses = str(r["total_courses"])
        
        if simulate_graduation and r.get("graduating_simulated"):
            credits_str = f"{r['total_credits']} (Grad)"
        else:
            credits_str = str(r["total_credits"])

        if r["missing_courses_count"] == 0:
            missing_str = "None (100% matched)"
            missing_disp = f"{Colors.GREEN}{missing_str:<{col_widths[5]}}{Colors.RESET}"
        else:
            first_m = r["missing_courses"][0]["title"]
            if r["missing_courses_count"] > 1:
                missing_str = f"{r['missing_courses_count']} ({truncate(first_m, 18)}, +{r['missing_courses_count']-1})"
            else:
                missing_str = f"1 ({truncate(first_m, 22)})"
            missing_disp = f"{Colors.YELLOW}{missing_str:<{col_widths[5]}}{Colors.RESET}"

        if no_pdf:
            pdf_str = "Skipped"
            pdf_disp = f"{Colors.DIM}{pdf_str:^{col_widths[6]}}{Colors.RESET}"
        elif r["pdf_compiled"]:
            pdf_str = "Generated"
            pdf_disp = f"{Colors.GREEN}{pdf_str:^{col_widths[6]}}{Colors.RESET}"
        else:
            pdf_str = "Failed"
            pdf_disp = f"{Colors.RED}{pdf_str:^{col_widths[6]}}{Colors.RESET}"

        status = r["status"]
        if status == "PASS":
            status_disp = f"{Colors.GREEN}{Colors.BOLD} PASS {Colors.RESET}"
        elif status == "WARNING":
            status_disp = f"{Colors.YELLOW}{Colors.BOLD} WARN {Colors.RESET}"
        else:
            status_disp = f"{Colors.RED}{Colors.BOLD} FAIL {Colors.RESET}"

        row_content = (
            f"| {name:<{col_widths[0]}} "
            f"| {major:^{col_widths[1]}} "
            f"| {semesters:^{col_widths[2]}} "
            f"| {courses:^{col_widths[3]}} "
            f"| {credits_str:^{col_widths[4]}} "
            f"| {missing_disp} "
            f"| {pdf_disp} "
            f"| {status_disp} |"
        )
        print(row_content)

    print(sep_line)

    # Summary Counts
    passed = sum(1 for r in results if r["status"] == "PASS")
    warnings = sum(1 for r in results if r["status"] == "WARNING")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    graduated = sum(1 for r in results if r.get("graduating_simulated"))
    total = len(results)

    print(f"\n{Colors.BOLD}Test Execution Summary:{Colors.RESET}")
    print(f"  • Total Tests:    {total}")
    print(f"  • {Colors.GREEN}Passed:{Colors.RESET}         {passed}")
    print(f"  • {Colors.YELLOW}With Warnings:{Colors.RESET}  {warnings} (missing catalog entries)")
    print(f"  • {Colors.RED}Failed:{Colors.RESET}         {failed}")
    if simulate_graduation:
        print(f"  • {Colors.CYAN}Simulated Degree Completions:{Colors.RESET} {graduated}/{total} student(s) graduated\n")
    else:
        print()


def generate_markdown_report(results: list, report_file: Path, no_pdf: bool, simulate_graduation: bool = False):
    """Generate a clean, professional markdown report for human checking."""
    passed = sum(1 for r in results if r["status"] == "PASS")
    warnings = sum(1 for r in results if r["status"] == "WARNING")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    graduated = sum(1 for r in results if r.get("graduating_simulated"))

    lines = [
        "# 📋 Transcript Verification & Test Suite Report",
        "",
        f"**Generated On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Total Test Transcripts:** {len(results)} | **Passed:** {passed} | **Warnings:** {warnings} | **Failed:** {failed}  ",
        f"**PDF Compilation Mode:** {'Skipped (--no-pdf)' if no_pdf else 'Enabled (XeLaTeX)'}  ",
        f"**Graduation Planner Simulation:** {'Enabled (--simulate-graduation)' if simulate_graduation else 'Disabled (Raw Transcripts)'}",
        "",
        "---",
        "",
        "## 📊 Executive Summary Table",
        "",
        "| Test / Student | Major | Semesters | Courses | Total Credits | Graduated? | Missing Courses | PDF Status | Overall Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: |"
    ]

    for r in results:
        status_badge = "🟢 PASS" if r["status"] == "PASS" else ("🟡 WARNING" if r["status"] == "WARNING" else "🔴 FAIL")
        pdf_badge = "✅ Built" if r["pdf_compiled"] else ("⏸️ Skipped" if no_pdf else "❌ Failed")
        missing_label = "None" if r["missing_courses_count"] == 0 else f"{r['missing_courses_count']} missing"
        test_link = f"[{r['test_name']}](#{r['test_name'].lower().replace('_', '-')})"
        grad_badge = f"🎓 Yes ({len(r.get('graduating_courses', []))} crses)" if r.get("graduating_simulated") else ("In Progress" if simulate_graduation else "—")

        lines.append(
            f"| **{test_link}** | {r['major']} | {r['total_semesters']} | {r['total_courses']} | "
            f"{r['total_credits']} | {grad_badge} | {missing_label} | {pdf_badge} | {status_badge} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 🔍 Detailed Test Case Analysis",
        ""
    ])

    for r in results:
        tname = r["test_name"]
        lines.append(f"### 👤 Test Case: `{tname}`\n")
        lines.append(f"- **Student Folder:** [`tests/{tname}/`](file://{TESTS_DIR / tname})")
        lines.append(f"- **Input Transcript:** [`{r['transcript_file']}`](file://{BASE_DIR / r['transcript_file']})")
        lines.append(f"- **Structured Answer JSON:** [`summary.json`](file://{TESTS_DIR / tname / 'summary.json'})")
        if r["pdf_compiled"]:
            lines.append(f"- **Generated Course Description:** [`CourseDescription.pdf`](file://{TESTS_DIR / tname / 'CourseDescription.pdf'})")
            lines.append(f"- **Generated Master TeX:** [`main.tex`](file://{TESTS_DIR / tname / 'main.tex'})")
        lines.append(f"- **Detected Academic Context:** {r['degree_level']} in {r['major']}")
        lines.append(f"- **Total Registered/Passed Credits:** {r['total_credits']} credits across {r['total_semesters']} terms ({r['total_courses']} courses)")

        if r.get("graduating_simulated"):
            lines.append(f"- **Degree Completion Status:** 🎓 **Simulated Graduation Successful!** ({len(r['graduating_courses'])} final courses added, bringing cumulative total to {r['total_credits']} credits)")
            lines.append(f"  - **Planned Courses:** {', '.join(f'`{cid}`' for cid in r['graduating_courses'])}")
        elif r.get("graduating_note"):
            lines.append(f"- **Degree Completion Status:** ⏳ {r['graduating_note']}")

        if r["error_message"]:
            lines.append(f"\n> [!CAUTION]\n> **Error:** {r['error_message']}\n")

        # Missing courses breakdown
        if r["missing_courses"]:
            lines.append("\n#### ⚠️ Missing Courses Not Found in Catalog:")
            lines.append("| Missing Course Title | Credits | Academic Term | Suggested Catalog ID |")
            lines.append("| :--- | :---: | :--- | :--- |")
            for m in r["missing_courses"]:
                lines.append(f"| **{m['title']}** | {m['credits']} | {m['term']} | `{m['suggested_id']}` |")
            lines.append("\n*To add these courses to the catalog, create `data/courses/<suggested_id>.json` or add an alias to `data/aliases.json`.*")
        else:
            lines.append("\n> [!NOTE]\n> **Catalog Match:** All courses were successfully matched against the syllabus catalog.")

        # Semester-by-semester breakdown table
        lines.append("\n#### 📚 Parsed Curriculum by Semester:")
        for s in r["semesters"]:
            heading = s["display_heading"] or s["term_name"]
            summer_note = " *(Summer Term - No GPA/Credit impact)*" if s["is_summer"] else f" *({s['semester_credits']} credits)*"
            lines.append(f"<details><summary><b>{heading}</b>{summer_note} — {s['courses_count']} course(s)</summary>\n")
            lines.append("| # | Course Title | Credits | Catalog ID | Type | Match Status |")
            lines.append("| :-: | :--- | :-: | :--- | :--- | :---: |")
            for idx, c in enumerate(s["courses"], 1):
                match_icon = "⚠️ Missing" if c["is_missing"] else "✅ Matched"
                cid_code = f"`{c['course_id']}`" if c["course_id"] else "—"
                lines.append(f"| {idx} | {c['title']} | {c['credits']} | {cid_code} | {c['type']} | {match_icon} |")
            lines.append("\n</details>\n")

        lines.append("\n---\n")

    lines.extend([
        "## 🛠️ Instructions for Manual Review",
        "",
        "1. **Inspect Generated PDFs:**",
        "   Open `tests/<student_name>/CourseDescription.pdf` to visually verify cover page details, curriculum overview tables, semester divider pages, and course description layouts.",
        "2. **Check Missing Courses:**",
        "   Review the missing courses flagged above. If a course is missing because of an alternate title spelling, map it in `data/aliases.json`. If it is a new elective, create its course file in `data/courses/<course_id>.json`.",
        "3. **Verify Course Credits & Semesters:**",
        "   Cross-reference `summary.json` against the original `transcript.pdf` to confirm that all terms, credit counts, and summer sessions reflect the student's official transcript record.",
        ""
    ])

    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"{Colors.CYAN}✓ Comprehensive test report saved to:{Colors.RESET} {report_file.relative_to(BASE_DIR)}")


def main():
    parser = argparse.ArgumentParser(
        description="Run automated tests on academic transcripts, report missing courses, and generate course descriptions."
    )
    parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional name(s) of specific student test directory to run (e.g. 'amir_barari', 'mani'). Runs all if omitted."
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Fast mode: Parse transcript and validate catalog matches, but skip XeLaTeX PDF compilation."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean previously generated outputs (summary.json, main.tex, CourseDescription.pdf) before running."
    )
    parser.add_argument(
        "--report",
        type=str,
        default=str(DEFAULT_REPORT_FILE),
        help=f"Path to markdown test report (default: {DEFAULT_REPORT_FILE.relative_to(BASE_DIR)})"
    )
    parser.add_argument(
        "--style",
        choices=["semester", "category"],
        default="semester",
        help="Course description layout style (default: semester)"
    )
    parser.add_argument(
        "--omit-general",
        action="store_true",
        help="Omit general education courses from course description pages"
    )
    parser.add_argument(
        "--omit-religion",
        action="store_true",
        help="Omit religious courses from course description pages"
    )
    parser.add_argument(
        "--simulate-graduation",
        action="store_true",
        help="Simulate degree completion by adding a final graduation semester (140–142 credits) for eligible students"
    )

    args = parser.parse_args()

    # Discover tests
    test_cases = find_test_directories(TESTS_DIR, requested_names=args.test_names if args.test_names else None)

    if not test_cases:
        print(f"{Colors.RED}[Error]{Colors.RESET} No test directories with transcript PDFs found in {TESTS_DIR}!")
        if args.test_names:
            print(f"Filter was: {args.test_names}")
        sys.exit(1)

    print("\n" + "=" * 68)
    print(f" {Colors.BOLD}University of Tehran Course Description — Transcript Test Runner{Colors.RESET}")
    print("=" * 68)
    print(f"• Found {len(test_cases)} test case(s) in {TESTS_DIR.name}/")
    print(f"• Mode: {'Fast Validation (No PDF)' if args.no_pdf else 'Full Build (XeLaTeX PDF Generation)'}")
    print(f"• Graduation Simulation: {'Enabled' if args.simulate_graduation else 'Disabled'}")
    print(f"• Style: {args.style}")
    print("=" * 68 + "\n")

    results = []

    for idx, (student_dir, pdf_path) in enumerate(test_cases, 1):
        test_name = student_dir.name
        print(f"[{idx}/{len(test_cases)}] Running Test: {Colors.BOLD}{test_name}{Colors.RESET} ({pdf_path.name})...")

        if args.clean:
            clean_student_artifacts(student_dir)

        res = run_single_test(
            student_dir=student_dir,
            transcript_pdf=pdf_path,
            no_pdf=args.no_pdf,
            style=args.style,
            omit_general=args.omit_general,
            omit_religion=args.omit_religion,
            simulate_graduation=args.simulate_graduation
        )
        results.append(res)

        # Brief status line
        if res["status"] == "PASS":
            grad_note = f" [Graduated: {res['total_credits']} cr]" if res.get("graduating_simulated") else ""
            print(f"     {Colors.GREEN}✓ PASSED{Colors.RESET}: {res['total_courses']} courses across {res['total_semesters']} semesters.{grad_note}")
        elif res["status"] == "WARNING":
            print(f"     {Colors.YELLOW}⚠ WARNING{Colors.RESET}: {res['total_courses']} courses ({res['missing_courses_count']} missing from catalog).")
        else:
            print(f"     {Colors.RED}✗ FAILED{Colors.RESET}: {res.get('error_message')}")

    # Render terminal table
    render_terminal_table(results, no_pdf=args.no_pdf, simulate_graduation=args.simulate_graduation)

    # Save markdown report
    report_path = Path(args.report)
    generate_markdown_report(results, report_path, no_pdf=args.no_pdf, simulate_graduation=args.simulate_graduation)


if __name__ == "__main__":
    main()
