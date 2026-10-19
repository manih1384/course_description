# University of Tehran — Course Description Generator

This project is a reverse-engineered, modular Course Description document system for the **University of Tehran, School of Electrical and Computer Engineering**.

It allows you to **add, remove, edit, reorder, and filter courses and degree programs** while reproducing the original typography, visual styling, header/footer layout, emblems, watermarks, and pagination.

---

## 📁 Project Structure

```
course_description/
├── build.py                  # CLI build manager (generate LaTeX & compile PDF)
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
    ├── courses.json          # Complete course catalog (all 56 courses)
    └── courses/              # Individual modular JSON files for each course
        ├── physics_1.json
        ├── calculus_1.json
        ├── data_structures.json
        ├── artificial_intelligence.json
        └── ... (56 courses)
```

---

## 🚀 Quick Start

### 1. Build the Default Course Description PDF
To generate `main.tex` and compile `CourseDescription.pdf`:
```bash
./build.py
```
*(Uses XeLaTeX from TinyTeX automatically)*

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
