# 🎓 University of Tehran — Course Description Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![LaTeX: XeLaTeX](https://img.shields.io/badge/LaTeX-XeLaTeX-orange.svg)](https://tug.org/xetex/)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](README.md)

An open-source, modular Course Description document generator reverse-engineered for the **University of Tehran, School of Electrical and Computer Engineering (ECE)**.

Designed for undergraduate and graduate students applying to international MSc/Ph.D. programs who need official, high-quality, and personalized course description brochures that precisely match University of Tehran transcript records.

---

## ✨ Features

- **🏛 Official Visual Identity & Typography:** Faithfully reproduces University of Tehran official emblem, School of ECE header logo, background watermark, margins, headers/footers, and page numbering.
- **📄 Transcript-Driven Personalization:** Automatically parses official or unofficial UT English transcript PDFs and extracts all terms, courses, credits, and course categories.
- **📅 Chronological Curriculum Overview:** Formats semester-by-semester study tables with accurate credit counts, handling both regular terms and summer sessions.
- **🎓 Final Semester Graduation Planner:** Automatically identifies degree candidates close to finishing (140–142 credits) and lets you interactively or programmatically append planned graduation courses.
- **🗂 Flexible Document Styles:**
  - `semester` (default): Chronological term-by-term order with clean semester divider title pages.
  - `category`: Grouped hierarchically by academic classification (*Basic* $\rightarrow$ *Major* $\rightarrow$ *Specialized* $\rightarrow$ *Elective* $\rightarrow$ *General* $\rightarrow$ *Workshop* $\rightarrow$ *Internship* $\rightarrow$ *Project*).
- **✂️ Omission Filters:** Exclude non-technical coursework (`--omit-general`, `--omit-religion`) while preserving full credit totals on the overview table.
- **🔌 Zero Mandatory Pip Dependencies:** Core generation and transcript matching run entirely on standard Python 3.8+.

---

## 📁 Project Structure

```
course_description/
├── build.py                  # CLI build manager (generates LaTeX & compiles PDF)
├── transcript_parser.py      # Transcript parser & fuzzy catalog course matcher
├── test_transcripts.py       # Automated validation test suite
├── main.tex                  # Active master LaTeX document (for XeLaTeX)
├── CourseDescription.pdf     # Default compiled PDF output
├── LICENSE                   # MIT License
├── CONTRIBUTING.md           # Guide for adding/editing courses
├── templates/
│   └── template.tex          # Master LaTeX template (watermark, headers, footers)
├── assets/
│   ├── cover_logo.png        # University of Tehran coat of arms emblem
│   ├── header_logo.png       # School of ECE header logo
│   └── watermark.png         # Centered page background watermark
├── data/
│   ├── programs.json         # Degree programs (CE & EE sequences)
│   ├── courses.json          # Master course catalog
│   ├── course_filters.json   # General and religious course filter keywords
│   ├── aliases.json          # Fuzzy match aliases for variant transcript titles
│   └── courses/              # Modular JSON definitions for individual courses
└── tests/
    ├── sample_student/       # Public mock transcript fixture (transcript.txt)
    └── test_report.md        # Comprehensive verification report
```

---

## 🐧 Linux Quick Setup (From Scratch)

The system is tested and optimized for Linux out-of-the-box. Follow the instructions for your distribution below:

### 1. Ubuntu / Debian / Pop!_OS / Linux Mint
```bash
sudo apt update
sudo apt install -y python3 poppler-utils texlive-xetex texlive-fonts-recommended
```

### 2. Arch Linux / Manjaro
```bash
sudo pacman -Syu --needed python poppler texlive-xetex
```

### 3. Fedora / RHEL
```bash
sudo dnf install -y python3 poppler-utils texlive-scheme-medium
```

*(macOS: `brew install poppler && brew install --cask mactex-no-gui` | Windows: `choco install poppler miktex`)*

### 4. Verify Your Environment
Run the built-in diagnostic checker:
```bash
./build.py --check-env
```
You should see checkmarks ($\checkmark$) for Python, `pdftotext`, XeLaTeX, and all required assets.

---

## 🚀 Quick Start

### 1. Build the Complete Default Brochure (Computer Engineering)
```bash
./build.py
```
This generates `main.tex` and compiles `CourseDescription.pdf` containing the full curriculum brochure.

### 2. Build the Electrical Engineering Brochure
```bash
./build.py --major ee --output EE_CourseDescription.pdf
```

### 3. Generate a Personalized Brochure from Your Transcript
Drop your official or unofficial transcript PDF (or plain text) into the project and run:
```bash
./build.py --transcript my_transcript.pdf
```
This creates a tailored course description document containing **only the courses you have completed**, sequenced semester by semester with large divider pages and credit totals.

### 4. Common CLI Options

| Command | Description |
| :--- | :--- |
| `./build.py` | Build standard Computer Engineering brochure |
| `./build.py --major ee` | Build standard Electrical Engineering brochure |
| `./build.py --transcript t.pdf` | Build personalized brochure from transcript |
| `./build.py --transcript t.pdf --style category` | Order courses by academic category instead of semester |
| `./build.py --transcript t.pdf --omit-religion` | Omit religious courses from syllabus pages |
| `./build.py --transcript t.pdf --omit-general` | Omit all general education courses (technical-only brochure) |
| `./build.py --no-pdf` | Generate `main.tex` without invoking XeLaTeX |
| `./build.py --list-courses` | List all 60+ courses in the catalog |
| `./build.py --list-programs` | List registered academic programs |

---

## 🎓 Final Semester Graduation Planner

When applying for Master's or Ph.D. programs before graduation, admission committees often require proof of a complete 140–142 credit undergraduate degree.

If your transcript indicates that you are in your final academic year (remaining credits $\le 24$):
1. **Interactive Prompt:** Running `./build.py --transcript my_transcript.pdf` will detect your status and offer to plan your final semester.
2. **Category Selection:** You can interactively select your remaining required laboratories, general electives, and specialized courses.
3. **Automated/CI Mode:** Specify future courses directly via flags:
   ```bash
   ./build.py --transcript my_transcript.pdf \
     --future-courses project distributed_systems generative_models computer_networks_laboratory
   ```

---

## 🧪 Automated Testing & Validation

The test harness validates catalog matching, semester parsing, and document generation:

```bash
# Fast test run across all test fixtures (without PDF compilation)
python3 test_transcripts.py --no-pdf

# Test only the public sample fixture
python3 test_transcripts.py --no-pdf sample_student

# Full test with XeLaTeX compilation
python3 test_transcripts.py
```
Test results and coverage are tracked in [`tests/test_report.md`](tests/test_report.md).

---

## 🤝 Contributing

Contributions of new course syllabi, textbooks, or degree programs are welcome!  
Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines on the course schema, CLI scaffolding, and testing your changes.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Emblems and university insignia are property of the University of Tehran and School of ECE and are provided solely for official academic student use.
