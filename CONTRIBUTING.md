# 🤝 Contributing to the University of Tehran Course Description Catalog

Thank you for your interest in contributing! This project is maintained to ensure that every student at the University of Tehran School of Electrical and Computer Engineering (and related engineering departments) has access to complete, high-quality, and official course descriptions for international graduate applications.

---

## 🧭 Repository Architecture

Courses in this repository are managed using a modular, decoupled JSON catalog:

```
data/
├── courses/              # Individual course JSON definitions (one file per course)
│   ├── calculus_1.json
│   ├── computer_vision.json
│   ├── generative_models.json
│   └── ...
├── courses.json          # Compiled master catalog (fast lookup cache)
├── programs.json         # Degree program curriculum sequences (CE & EE)
├── aliases.json          # Transcript title fuzzy-matching dictionary
└── course_filters.json   # Keywords for filtering non-technical courses
```

---

## ➕ Adding a New Course

You can add a new course either using the built-in CLI tool or by creating a JSON file directly.

### Method 1: Using the CLI Tool (Recommended)

Run `./build.py --add-course` with command-line arguments, or omit them to enter interactive prompt mode:

```bash
./build.py --add-course \
  --id deep_learning \
  --title "Deep Learning" \
  --credits 3 \
  --type "Elective | Theoretical" \
  --hours "48h Theoretical" \
  --prereq "Artificial Intelligence" \
  --objectives "Comprehensive introduction to deep neural networks, optimization algorithms, convolutional networks, recurrent architectures, transformers, and representation learning." \
  --syllabus "1. Introduction to Deep Learning\n2. Optimization and Backpropagation\n3. Convolutional Neural Networks (CNNs)\n4. Sequence Modeling and Transformers\n5. Generative and Self-Supervised Learning" \
  --textbooks "1. Ian Goodfellow, Yoshua Bengio, and Aaron Courville, Deep Learning, MIT Press, 2016." \
  --layout standalone
```

This will automatically create `data/courses/deep_learning.json`, sync `data/courses.json`, and register the course in the default program.

---

### Method 2: Manual JSON Specification

Create a new file under `data/courses/<course_id>.json`:

```json
{
  "id": "deep_learning",
  "index": 61,
  "title": "Deep Learning",
  "credits": "3",
  "type": "Elective | Theoretical",
  "prerequisites": "Artificial Intelligence",
  "hours": "48h Theoretical",
  "objectives": "Detailed academic paragraph describing the course purpose, foundational concepts, and student learning outcomes...",
  "syllabus": "1. Module 1: Foundational Theory\n2. Module 2: Optimization and Training\n3. Module 3: Advanced Architectures",
  "textbooks": "1. Author Name, Book Title, Edition, Publisher, Year.\n2. Second Author, Second Book Title, Publisher.",
  "layout": "standalone"
}
```

#### JSON Field Specifications:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `string` | Unique `snake_case` identifier (e.g. `generative_models`). |
| `index` | `int` or `null` | Sequential course catalog index (optional). |
| `title` | `string` | Official course name in English matching transcript records. |
| `credits` | `string` | Credit value as a string integer (e.g. `"3"`). |
| `type` | `string` | Academic classification: `"Basic \| Theoretical"`, `"Major \| Theoretical"`, `"Specialized \| Theoretical"`, `"Elective \| Theoretical"`, `"General \| Theoretical"`, `"Workshop"`, or `"Practical"`. |
| `prerequisites` | `string` or `null`| Course title(s) required beforehand, or `null`. |
| `hours` | `string` | Official training hours (typically `16h` per theoretical credit, `32h` per practical credit, e.g. `"48h Theoretical"`). |
| `objectives` | `string` | Rigorous academic paragraph outlining course goals, principles, and competencies. |
| `syllabus` | `string` | Multi-line syllabus. Numbered topics (`1. Introduction...`) or bulleted topics (`- Chapter: ...`) are supported. |
| `textbooks` | `string` or `null` | Numbered list of authoritative references and textbooks. |
| `layout` | `string` | `"standalone"` (default; starts on a fresh page) or `"compact"` (combines multiple courses per page for short 1-cr general courses). |

---

## 🔗 Linking to Programs & Aliases

### 1. Update `data/programs.json`
Add the new course ID to the appropriate degree sequence in `data/programs.json` (e.g., under `computer_engineering_bsc` or `electrical_engineering_bsc`):

```json
"courses": [
  ...
  "fundamentals_of_cognitive_science",
  "generative_models",
  "deep_learning",
  "project"
]
```

### 2. Update `data/courses.json`
Sync the master catalog by running:
```bash
python3 -c '
import json
with open("data/courses/deep_learning.json") as f:
    c = json.load(f)
with open("data/courses.json") as f:
    cat = json.load(f)
cat[c["id"]] = c
with open("data/courses.json", "w") as f:
    json.dump(cat, f, indent=2, ensure_ascii=False)
'
```

### 3. Add Transcript Aliases in `data/aliases.json`
Official UT transcripts often contain alternate transliterations, typos, or abbreviated course names. Add common variants to `data/aliases.json`:

```json
"aliases": {
  "deep learning": "deep_learning",
  "introduction to deep learning": "deep_learning",
  "deep neural networks": "deep_learning"
}
```

---

## 🧪 Verification & Testing

Before submitting a pull request, run the automated verification suite to ensure everything compiles and matches:

1. **Verify Environment:**
   ```bash
   ./build.py --check-env
   ```
2. **Verify Catalog Listing:**
   ```bash
   ./build.py --list-courses
   ```
3. **Run Transcript Test Suite:**
   ```bash
   python3 test_transcripts.py --no-pdf
   ```
   *Make sure all test cases report `PASS` with `0 missing courses`.*

4. **Verify LaTeX Generation:**
   ```bash
   ./build.py --no-pdf
   ```

---

## 📝 Pull Request Guidelines

- Ensure JSON files are valid and formatted with `ensure_ascii=False` (2 spaces indentation).
- Course objectives and syllabi should be written in formal academic English.
- Avoid personal details, student grades, or machine-specific paths in any committed file.

