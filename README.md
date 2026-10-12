# 🎯 PrepTrack — Placement Preparation Tracker

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.x-FF6384?style=flat&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A modern, full-stack web application designed for students and graduates to organize, monitor, and visualize their campus placement preparation across **Data Structures & Algorithms (DSA)**, **Aptitude practice**, and **Mock Assessments**.

---

## 📸 Screenshots & Visual Preview

<!-- Replace these placeholder paths with your actual screenshots after running the app -->
<div align="center">
  <img src="docs/screenshots/dashboard-preview.png" alt="PrepTrack Dashboard Preview" width="850" onerror="this.src='https://via.placeholder.com/850x450/18233b/ffffff?text=PrepTrack+Dashboard+Preview+%28Add+screenshot+to+docs%2Fscreenshots%29';"/>
  <p><em>Main Dashboard — Live 5-Card Metrics, 7-Day Momentum Timeline, and Interactive Chart.js Visualizations</em></p>
</div>

<br/>

<div align="center">
  <img src="docs/screenshots/dsa-search-filters.png" alt="DSA Filter Toolbar and Modal" width="850" onerror="this.src='https://via.placeholder.com/850x380/18233b/ffffff?text=DSA+Question+List+%26+Search%2FFilters+%28docs%2Fscreenshots%29';"/>
  <p><em>Instant DSA Search, Dynamic Multi-Filter Toolbar, and Modal Editor</em></p>
</div>

---

## ✨ Key Features

### 1. 💻 DSA Problem Tracker
- **CRUD Operations**: Log coding questions with problem title, algorithmic topic, and difficulty level (`Easy`, `Medium`, `Hard`).
- **One-Click Toggle**: Switch status between **Pending** and **Completed** with automatic completion timestamping.
- **Search & Multi-Filters**:
  - Live, client-side search by question title.
  - Server-side filter parameters by topic, difficulty, and completion status.
  - 1-click **Clear Filters** reset.
- **In-Place Modal Editing**: Quickly update question details directly from the dashboard without navigating away, with a dedicated fallback editing route (`/edit-dsa/<id>`).

### 2. 📚 Aptitude Practice Logger
- Track topics practiced (e.g., *Percentages*, *Time & Work*, *Probability*).
- Log problem count and practice duration (minutes spent) along with the practice date.
- Instant calculation of total questions solved and weekly study hours.

### 3. 📝 Mock-Test Performance Evaluator
- Record test names (e.g., *TCS NQT Mock*, *CoCubes Diagnostic*, *AMCAT*), scored marks, total marks, and assessment dates.
- Automatic percentage score calculation and average score tracking.

### 4. 📊 Data-Driven Visual Analytics (Chart.js)
- **DSA Completion Donut Chart**: Pending vs. Completed ratio with custom emerald and amber color palette and interactive percentage tooltips.
- **Mock-Test Score Trend**: Chronological line chart tracking percentage scores over time with smooth spline curves and filled gradient background.
- **Aptitude Volume Chart**: Daily bar chart displaying questions solved per practice date with duration tooltips.
- **Graceful Empty State Handling**: Elegant empty placeholders guide users when no data exists yet, preventing blank canvases or errors.

### 5. 🔥 Practice Streak & Rolling 7-Day Momentum
- **Consecutive Practice Streak**: Calculates active daily streak across all activities (DSA creation/completion, aptitude sessions, mock tests). If you practiced yesterday, the streak remains active today so you never lose motivation.
- **Rolling 7-Day Window**: Computes active study consistency (`X of 7 days`), weekly DSA problems solved, weekly aptitude volume, and mock test averages.
- **Interactive Day Pills**: Visual 7-day indicators with active status rings and a highlighted badge for today.

### 6. 🛡️ Security & Reliability
- **Parameterized SQL**: All database operations use parameterized queries (`?`) to prevent SQL injection vulnerabilities.
- **Robust Validation**: Frontend and backend length bounds, range limits, calendar date checks, and protection against `NaN` / `Infinity` inputs.
- **Automatic Migration**: Local SQLite database tables and schema migrations initialize automatically on first startup without resetting existing user records.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3, Flask 3.x |
| **Database** | SQLite 3 |
| **Frontend** | HTML5 Semantic Markup, Vanilla CSS3 (Custom Design System), JavaScript (ES6+) |
| **Visualizations** | Chart.js 4.x |
| **Typography** | Google Fonts (*DM Sans* & *Manrope*) |
| **Testing** | Python `unittest` framework |

---

## 📂 Project Structure

```text
PrepTrack/
│
├── app.py                  # Core Flask backend, route handlers, validations, & analytics engine
├── test_app.py             # Automated unit test suite (17 comprehensive tests)
├── requirements.txt        # Python dependency manifest
├── .gitignore              # Git ignore rules (excludes virtual environments, database, cache)
├── .env.example            # Environment configuration template
├── README.md               # Project documentation and setup guide
│
├── static/
│   └── style.css           # Vanilla CSS design system, typography, animations, & mobile breakpoints
│
├── templates/
│   ├── index.html          # Main dashboard, visual charts, forms, tables, and modal editor
│   └── edit_dsa.html       # Standalone fallback editing template
│
└── docs/
    └── screenshots/        # Directory for portfolio screenshots and preview images
```

---

## 🚀 Getting Started

Follow these step-by-step instructions to set up and run PrepTrack locally.

### Prerequisites
- **Python 3.10+** installed on your system. ([Download Python](https://www.python.org/downloads/))
- **Git** installed on your system. ([Download Git](https://git-scm.com/))

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/PrepTrack.git
cd PrepTrack
```

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*(If PowerShell displays a script execution policy error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and retry activation).*

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

### 5. Run the Application
```bash
python app.py
```

The terminal will display:
```text
 * Running on http://127.0.0.1:5000
```

Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.

> 💡 **Database Auto-Initialization:** The SQLite database (`placement_tracker.db`) is automatically created and configured on the very first run. No manual SQL scripts are required!

---

## 🧪 Running Automated Unit Tests

PrepTrack includes a comprehensive automated test suite with **17 test cases** testing database migrations, validation rules, streak logic, search/filtering, modal edits, and chart analytics payloads.

Run all tests using Python's built-in `unittest` runner:

```powershell
python -m unittest test_app.py -v
```

**Expected Result:**
```text
Ran 17 tests in ~1.2s

OK
```

---

## 📖 How to Test Main Features

1. **Add a DSA Question**: Use the *Add DSA question* card. Enter a title (e.g., `Binary Search`), topic (`Algorithms`), select a difficulty, and click **+ Add question**.
2. **Toggle Completion**: In the DSA table, click the **Complete** button. The question status changes to **Completed**, the progress bar increments, and the **DSA Completion Donut Chart** updates.
3. **Edit a Question**: Click **Edit** on any row to open the modal dialog. Modify the title or difficulty and save changes.
4. **Search and Filter**: Type in the search box to test instant filtering. Select a topic or difficulty dropdown to refine results. Click **Clear** to reset.
5. **Log Aptitude Session**: Enter an aptitude topic (e.g., `Time and Distance`), solve count, minutes, and pick today's date. Notice the **Aptitude Practice Chart** and weekly stats update.
6. **Record a Mock Test**: Enter a test name, score, total marks, and date. Notice the **Mock-Test Trend Chart** plotting your percentage.
7. **Check Daily Streak & 7-Day Momentum**: View your active streak badge and the 7-day consistency indicators in the **Weekly Momentum** section.

---

## 🔒 Security Best Practices

- **Zero Credential Leakage**: No hardcoded passwords, tokens, or sensitive user data are committed.
- **SQL Injection Defense**: Every SQLite query uses parameterized placeholders (`?`).
- **Environment Isolation**: Local database files (`*.db`), virtual environments (`.venv/`), and `.env` files are ignored via `.gitignore`.
- **Safe Type Parsing**: Floating point values are checked against `NaN` and `Infinity` before database insertion.

---

## 🗺️ Roadmap & Future Enhancements

- [ ] User authentication (Login / Signup with Flask-Login & bcrypt)
- [ ] Export practice records to CSV and PDF report cards
- [ ] Company-specific tags (e.g., *Amazon*, *TCS*, *Infosys*, *Google*)
- [ ] Dark Mode toggle with persistent preference

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — feel free to use, modify, and distribute for learning and portfolio purposes.

---

<div align="center">
  <strong>Built with dedication for campus placement preparation.</strong><br/>
  ⭐ If you found this project helpful, please consider starring the repository!
</div>
