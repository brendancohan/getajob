# 🎯 getajob: Autonomous Job Search & AI Triage Pipeline

[![OpenCode Skill](https://img.shields.io/badge/OpenCode-Skill-blue.svg)](https://opencode.ai)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-purple.svg)](https://anthropic.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end, model-agnostic agentic workflow and skill designed for **OpenCode**, **Claude Code**, and autonomous coding agents. It automates the entire job search lifecycle: **multi-platform job scraping**, **batched AI qualification triage**, **structured CSV database tracking**, and **tailored ATS-optimized application generation (Markdown + Word `.docx`)**.

---

## 🏗️ How It Works (The 2-Stage Pipeline)

```
[ Automated Nightly Schedule (Systemd / Cron / Windows Task Scheduler @ 2:00 AM) ]
       │
       ▼
[ Stage 1: Ingestion (`scripts/job_scraper.py`) ]
   • Aggregates fresh job listings across Indeed, LinkedIn, ZipRecruiter, and Glassdoor using `python-jobspy`.
   • Deduplicates links against your active `tracking.csv` database.
   • Ingests new discoveries into `tracking.csv` with `Status: Unscreened`.
       │
       ▼
[ Stage 2: AI Triage Agent (`scripts/ai_triage.py`) ]
   • Reads all newly discovered `Unscreened` listings.
   • Loads candidate context dynamically from `base_resume.md` and `criteria.md`.
   • Evaluates jobs in token-efficient batches (25 jobs per request).
   • Evaluates Seniority Ceilings, Capability Match, Disqualifiers, and Clearances.
   • Assigns a 0–100 Qualification Score and 1-sentence rationale:
       - Score >= 70 ➔ Promoted to `Status: Pending` (ready for your review).
       - Score < 70 ➔ Marked `Status: Skipped` with logged reasoning.
       │
       ▼
[ Morning Interactive Review with Your AI Agent ]
   • You only review pre-vetted, high-conviction jobs (`Status == 'Pending'`).
   • Rapid "Proceed" or "Pass" triage per job.
   • For "Proceed" jobs, your agent generates customized resumes and cover letters in `applications/`.
   • Compiles to clean, ATS-compliant Word documents (`.docx`) using `scripts/document_compiler.py`.
   • Tracks all submissions in `tracking.csv` as `Status: Applied`.
```

---

## 📁 Repository Structure

```text
getajob/
├── SKILL.md                              # The universal Skill definition (OpenCode / Claude Code)
├── scripts/
│   ├── job_scraper.py                   # Multi-platform job board aggregator
│   ├── ai_triage.py                     # Batched LLM qualification evaluator
│   └── document_compiler.py             # Pandoc Markdown to .docx conversion script
└── templates/
    ├── base_resume.template.md          # Comprehensive career history & achievements template
    ├── criteria.template.md             # Role targeting, tech stack, salary floor & disqualifiers
    ├── master_cover_letter.template.md  # Standardized cover letter template
    ├── tracking.template.csv            # Central lifecycle database schema
    ├── job-pipeline.service.template    # Systemd oneshot background service definition
    ├── job-pipeline.timer.template      # Systemd 2:00 AM calendar timer definition
    ├── run-job-pipeline.ps1.template    # Windows PowerShell runner script
    └── register-windows-task.ps1.template # Windows Task Scheduler registration script
```

---

## 🚀 Quickstart & Setup

### 1. Installation as an Agent Skill

#### **For OpenCode Users:**
Install globally in your user configuration:

* **Linux / macOS (Bash):**
  ```bash
  git clone git@github.com:brendancohan/getajob.git ~/.config/opencode/skills/job-search-pipeline
  ```
* **Windows (PowerShell):**
  ```powershell
  git clone git@github.com:brendancohan/getajob.git "$env:USERPROFILE\.config\opencode\skills\job-search-pipeline"
  ```
*Or install locally in a project directory under `.opencode/skills/job-search-pipeline`.*

#### **For Claude Code Users:**
Install globally in your Claude skills directory:

* **Linux / macOS (Bash):**
  ```bash
  git clone git@github.com:brendancohan/getajob.git ~/.claude/skills/job-search-pipeline
  ```
* **Windows (PowerShell):**
  ```powershell
  git clone git@github.com:brendancohan/getajob.git "$env:USERPROFILE\.claude\skills\job-search-pipeline"
  ```
*Or install locally in a project directory under `.claude/skills/job-search-pipeline`.*

---

### 2. Workspace Initialization

In your local job search project folder:

1. **Create and activate a Python virtual environment:**
   * **Linux / macOS (Bash):**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install python-jobspy pandas pypandoc markdown beautifulsoup4 requests
     ```
   * **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     pip install python-jobspy pandas pypandoc markdown beautifulsoup4 requests
     ```

2. **Establish your profile and tracking files:**
   * **Linux / macOS (Bash):**
     ```bash
     # Copy templates into your workspace root
     cp templates/base_resume.template.md base_resume.md
     cp templates/criteria.template.md criteria.md
     cp templates/tracking.template.csv tracking.csv
     mkdir -p applications scripts
     cp scripts/* scripts/
     ```
   * **Windows (PowerShell):**
     ```powershell
     # Copy templates into your workspace root
     Copy-Item templates\base_resume.template.md base_resume.md
     Copy-Item templates\criteria.template.md criteria.md
     Copy-Item templates\tracking.template.csv tracking.csv
     New-Item -ItemType Directory -Force -Path applications, scripts
     Copy-Item scripts\* scripts\
     ```

3. **Calibrate your profile:**
   * Edit `criteria.md` with your target roles, desired salary range, target tech stack, and hard disqualifiers.
   * Edit `base_resume.md` with your comprehensive career history, hard quantifiable metrics, and key technical deliverables.
   * Edit `scripts/job_scraper.py` to customize your search queries, target locations, and lookback window.

---

### 3. Usage & Daily Workflow

* **Run a Manual Scrape:**
  ```bash
  python scripts/job_scraper.py
  ```
* **Run the AI Triage Agent:**
  ```bash
  python scripts/ai_triage.py Unscreened 25
  ```
* **Pair Program with OpenCode or Claude:**
  Open your assistant in your project directory:
  ```bash
  opencode
  # or
  claude
  ```
  Simply prompt:
  > *"Review the next pending job in tracking.csv and let's tailor an application."*

---

### 4. Hands-Free Nightly Automation (Linux / Systemd & Windows / Task Scheduler)

To have your system automatically scrape and evaluate fresh jobs while you sleep:

#### **Linux (Systemd)**
1. Copy the systemd templates to your user service directory:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp templates/job-pipeline.service.template ~/.config/systemd/user/job-pipeline.service
   cp templates/job-pipeline.timer.template ~/.config/systemd/user/job-pipeline.timer
   ```
2. Update the paths in `job-pipeline.service` to point to your workspace directory and Python virtual environment.
3. Enable and start the timer:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now job-pipeline.timer
   ```

#### **Windows (Task Scheduler)**
1. Copy `templates\run-job-pipeline.ps1.template` to `run-job-pipeline.ps1` in your workspace and update `$WorkspaceDir`.
2. Copy `templates\register-windows-task.ps1.template` to `register-windows-task.ps1`, update `$ScriptPath`, and run it in PowerShell:
   ```powershell
   .\register-windows-task.ps1
   ```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
