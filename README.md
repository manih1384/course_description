# University of Tehran — Course Description Generator

This project is a reverse-engineered, modular Course Description document system for the **University of Tehran, School of Electrical and Computer Engineering**.

It allows you to **add, remove, edit, reorder, and filter courses and degree programs** while reproducing the original typography, visual styling, header/footer layout, emblems, watermarks, and pagination.

---

## 📁 Project Structure

```
course_description/
├── build.py                  # CLI build manager (generate LaTeX & compile PDF)
├── transcript_parser.py      # Transcript parser & fuzzy catalog course matcher
├── requirements.txt          # Python dependencies (standard library core + optional pypdf)
├── main.tex                  # Active master LaTeX document (can also compile manually)
├── CourseDescription.pdf     # Compiled PDF output
├── templates/
│   └── template.tex          # Master LaTeX template (margins, headers, footers, watermark)
├── assets/
│   ├── cover_logo.png        # University of Tehran coat of arms emblem
│   ├── header_logo.png       # School of ECE header logo
│   └── watermark.png         # Centered page background watermark
└── data/
    ├── programs.json         # Programs registry & curriculum course sequences
    ├── courses.json          # Complete course catalog (CE & EE courses)
    ├── course_filters.json   # Configurable religious and general course filters
    ├── aliases.json          # Course title aliases for fuzzy matching
    └── courses/              # Individual modular JSON files for each course
```

---

## ⚙️ Prerequisites & Setup

The tool is designed to work out-of-the-box on Linux, macOS, and Windows with **no hardcoded paths** and **no complex Python environments**.

### 1. Check Your Environment
Run the built-in diagnostic tool to verify your system setup:
```bash
./build.py --check-env
```

### 2. Requirements Overview
| Component | Requirement | Details |
| :--- | :--- | :--- |
| **Python** | Python 3.8+ | Core scripts use **100% Python Standard Library** (zero mandatory pip packages). |
| **PDF Extraction** | `pdftotext` *(Recommended)*<br>or `pypdf` *(Fallback)* | `pdftotext` (from Poppler) preserves transcript column layout.<br>If unavailable, run `pip install -r requirements.txt`. |
| **LaTeX Engine** | `xelatex` *(Recommended)*<br>or `pdflatex` | XeLaTeX provides full UTF-8 Unicode, Liberation/Times typography, and microtype. |

### 3. Quick OS Installation Commands

#### Ubuntu / Debian:
```bash
sudo apt update
sudo apt install -y poppler-utils texlive-xetex texlive-fonts-recommended
```

#### macOS (Homebrew):
```bash
brew install poppler
brew install --cask mactex-no-gui   # or full MacTeX: brew install --cask mactex
```

#### Windows:
Using Chocolatey or winget:
```powershell
# Using Chocolatey:
choco install poppler miktex

# Or using winget:
winget install MiKTeX.MiKTeX
```
*(If you do not want to install Poppler on Windows, simply run: `pip install -r requirements.txt`)*

#### Arch Linux / Fedora:
```bash
# Arch:
sudo pacman -S poppler texlive-xetex

# Fedora:
sudo dnf install poppler-utils texlive-scheme-medium
```

---

## 🚀 Quick Start

### 1. Build the Default Course Description PDF
To generate `main.tex` and compile `CourseDescription.pdf`:
```bash
./build.py
```
*(Automatically detects your installed XeLaTeX compiler)*

### 2. View Programs and Courses
- List all available degree programs:
  ```bash
  ./build.py --list-programs
  ```
- List all courses with credit counts and course types:
  ```bash
  ./build.py --list-courses
  ```
- List courses in a specific program:
  ```bash
  ./build.py --list-courses --program computer_engineering_bsc
  ```

### 3. Generate a Personalized Course Description from a Transcript
To parse an official or unofficial University of Tehran transcript PDF and generate a personalized document:
```bash
./build.py --transcript unofficial_transcript.pdf
```
- **Semester-by-Semester Curriculum Overview:** Inserts a structured table breakdown of all semesters (Semester 1–6, Summer Semester, Semester 7, etc.), course types, and credits.
- **Accurate Semester Numbering:** Summer semesters are labeled separately (e.g., `Summer Semester (2025–2026)`) and do not increment the regular semester count.
- **Large Semester Divider Pages:** In semester style, a dedicated title page is inserted before each term's courses (`SEMESTER 1`, `SUMMER SEMESTER`, etc.).
- **Missing Course Handling:** Identifies courses in the transcript that are missing from the catalog, prints a warning, marks them as `(Not Included in Syllabus)` in the overview, and skips generating empty course pages.
- **Document Styles (`--style`):**
  - `--style semester` (default for transcript): Chronological by semester with semester divider pages.
  - `--style category`: Grouped by classification (`Basic` $\rightarrow$ `Major` $\rightarrow$ `Specialized` $\rightarrow$ `Elective` $\rightarrow$ `General` $\rightarrow$ `Workshop` $\rightarrow$ `Internship` $\rightarrow$ `Project`).
- **Omission Filters:**
  - `--omit-general`: Omits general education courses from description pages.
  - `--omit-religion`: Omits religious courses from description pages.
  - Omitted courses remain listed on the Curriculum Overview table marked as `(Omitted from Syllabus)` to keep credit totals consistent with official transcripts.
  - Configurable and expandable via `data/course_filters.json`.
- **Major Selector (`--major`):**
  - `--major ce` (Computer Engineering): Cover Page sets program to *Computer Engineering*.
  - `--major ee` (Electrical Engineering): Cover Page sets program to *Electrical Engineering*.
  - School is uniformly set to *School of Electrical and Computer Engineering*.
  - Auto-detected from transcript PDF when available, with CLI `--major` acting as an explicit override.
- **Examples:**
  ```bash
  # Standard semester-by-semester build (auto-detects major)
  ./build.py --transcript unofficial_transcript.pdf

  # Build with explicit major switch (e.g. Electrical Engineering)
  ./build.py --transcript karname_eng.pdf --major ee

  # Build full Electrical Engineering brochure (43 courses)
  ./build.py --major ee --output EE_CourseDescription.pdf

  # Category-based ordering omitting religious courses
  ./build.py --transcript unofficial_transcript.pdf --style category --omit-religion

  # Technical-only syllabus omitting all general courses
  ./build.py --transcript unofficial_transcript.pdf --omit-general --output Technical_Syllabus.pdf
  ```

---

## 🎓 Final Semester Graduation Planner (Degree Completion)

When applying for graduate programs or master's admissions, students who are finishing their studies in the upcoming semester often need a **complete Course Description document** that includes their planned final semester courses to reflect a finished bachelor's degree.

### 📌 Eligibility & Credit Rules
1. **Graduation Eligibility:** A student can register for up to **24 credits** in their final graduation semester (ترم فراغت از تحصیل). If remaining credits to reach 140 are $\le 24$, the graduation planner activates.
2. **Degree Completion Window:** Total cumulative credits across all semesters must fall strictly in the **140–142 credit range** (anything $< 140$ is incomplete, anything $> 142$ exceeds degree requirements).
3. **Mandatory Capstone:** If `B.Sc. Project` (3 cr) has not been taken in earlier semesters, it is **strictly forced** into the final semester.
4. **0-Credit Internship Rule:** Industrial Training is a 0-credit graduation requirement and is excluded from regular semester load.
5. **Seamless Styling:** The final semester is rendered seamlessly as a standard regular semester (e.g., `Semester 8: Academic Year 2026–2027 (2nd Semester)`) with identical divider pages and course description formatting.

### 💻 Interactive Terminal Mode
When running `./build.py --transcript transcript.pdf`, if the student is eligible, the tool prompts:
```
🎓 Final Semester Graduation Planner (Degree Completion)
  • Current Passed Credits:    124 credits
  • Degree Completion Window:  140–142 credits (Remaining: 16–18 cr)
  • Max Final-Semester Cap:    24 credits
--------------------------------------------------------------------
You are eligible to graduate next semester! In case you are applying
for graduate programs, would you like to build your complete curriculum
by adding your planned final semester?

Build full curriculum including final semester? [y/N]: y
```
The user is then guided group-by-group through their untaken courses:
- **Group 1/3: Practical Laboratories & Workshops** (e.g. Computer Networks Lab, Computer Architecture Lab)
- **Group 2/3: General Education Courses** (e.g. Financial Literacy, Environmental Knowledge)
- **Group 3/3: Specialized & Elective Theory Courses** (e.g. Distributed Systems, Internet Engineering, Real-Time Embedded Systems)

### ⚡ Non-Interactive CLI Automation
For scripts, CI/CD, or automated builds, you can pass planned courses directly:
```bash
# Add specific future courses to reach graduation
./build.py --transcript tests/mani/transcript.pdf \
  --future-courses project distributed_systems internet_engineering real_time_embedded_systems computer_networks_laboratory computer_architecture_laboratory research_and_technical_presentation

# Force graduation planning prompt regardless of remaining credit check
./build.py --transcript transcript.pdf --graduating

# Disable prompts (for headless / batch usage)
./build.py --transcript transcript.pdf --no-prompt
```

---

## 🛠 Adding, Removing, and Modifying Courses

### Option A: Via the CLI

1. **Add a new course**:
   ```bash
   ./build.py --add-course \
     --id deep_learning \
     --title "Deep Learning" \
     --credits 3 \
     --type "Elective | Theoretical" \
     --hours "48h Theoretical" \
     --prereq "Artificial Intelligence" \
     --objectives "Introduction to deep neural networks, CNNs, RNNs, and transformers."
   ```
   *(This creates `data/courses/deep_learning.json` and adds it to the current program).*

2. **Remove a course from a program**:
   ```bash
   ./build.py --remove-course physical_education
   ```

3. **Rebuild**:
   ```bash
   ./build.py
   ```

---

### Option B: Via JSON Files (Direct & Modular)

Each course lives in its own simple JSON file under `data/courses/<course_id>.json`.

**Example Course JSON (`data/courses/physics_1.json`):**
```json
{
  "id": "physics_1",
  "title": "Physics 1",
  "credits": "3",
  "type": "Basic | Theoretical",
  "prerequisites": null,
  "hours": "48h Theoretical",
  "objectives": "The main goal of fundamental courses in physics...",
  "syllabus": "- Units, Physical Quantities, and Vectors:\n...\n- Motion along a Straight Line:\n...",
  "textbooks": "1. Fundamentals of Physics, David Halliday, Jearl Walker, Robert Resnick, 10th edition",
  "layout": "standalone"
}
```

- **Layout options:**
  - `"layout": "standalone"`: Starts on a fresh page (`\newpage`), used for Basic, Major, and Specialized courses.
  - `"layout": "compact"`: Flows together on pages (e.g. 3–4 courses per page), used for short General / Physical Education / Religion courses.

- **To edit a course:** Open the JSON file in `data/courses/`, edit text, and run `./build.py`.
- **To add a course:** Create a new `<new_course_id>.json` file in `data/courses/`, add its ID to `data/programs.json`, and run `./build.py`.
- **To remove a course:** Remove its ID from `data/programs.json` and run `./build.py`.
- **To reorder courses:** Simply change the order of IDs in the `"courses"` array in `data/programs.json`.

---

## 🎓 Managing Programs & Degrees

Programs are configured in `data/programs.json`:
```json
{
  "default_program": "computer_engineering_bsc",
  "programs": {
    "computer_engineering_bsc": {
      "program_name": "Computer Engineering",
      "degree": "Bachelor’s Degree",
      "degree_type": "bachelor",
      "courses": [
        "physics_1",
        "calculus_1",
        ...
      ]
    }
  }
}
```

### Adding a New Program (e.g. Master's Degree)
You can define a new program either by editing `data/programs.json` or running:
```bash
./build.py --add-program computer_engineering_msc --name "Computer Engineering" --degree "Master's Degree"
```
Then build that specific program:
```bash
./build.py --program computer_engineering_msc
```

---

## 🎯 Generating Tailored Subsets of Courses

If an application to a specific university only requires course descriptions for relevant core courses (e.g. Systems or AI courses), you can specify exactly which courses to include:
```bash
./build.py --courses data_structures algorithm_design_1 operating_system computer_networks database_design artificial_intelligence --output systems_ai_courses.pdf
```

---

## ⚙️ Manual Compilation with LaTeX
If you prefer to edit raw LaTeX directly, `build.py` maintains `main.tex`. You can compile it anytime with:
```bash
xelatex -interaction=nonstopmode main.tex
```

---

## 🧪 Automated Transcript Testing & Verification Suite

The repository includes a dedicated test harness (`test_transcripts.py`) to validate transcript parsing across diverse transcript formats and detect missing courses.

### Directory Organization
Each test transcript lives in its own student folder under `tests/`:
```
tests/
├── amir_barari/
│   ├── transcript.pdf          # Input transcript
│   ├── summary.json            # Structured answer (courses, credits, missing list)
│   ├── main.tex                # Generated LaTeX
│   └── CourseDescription.pdf   # Compiled PDF
├── artin_tavasoli/
├── daei/
├── mani/
└── test_report.md              # Overall test execution report
```

### Running Tests
- **Run all tests (fast parsing validation without compiling PDFs):**
  ```bash
  ./test_transcripts.py --no-pdf
  ```
- **Run all tests and compile CourseDescription PDFs for visual inspection:**
  ```bash
  ./test_transcripts.py
  ```
- **Run a single test case (e.g. `amir_barari`):**
  ```bash
  ./test_transcripts.py amir_barari
  ```
- **Run all tests and simulate degree completion for eligible students:**
  ```bash
  ./test_transcripts.py --simulate-graduation
  ```
- **Clean previous outputs before running:**
  ```bash
  ./test_transcripts.py --clean
  ```
- **View summary report:**
  After each run, an executive summary table is printed to the terminal, and an exhaustive markdown report is written to `tests/test_report.md`.

