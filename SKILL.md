---
name: job-search-pipeline
description: End-to-end autonomous job search, multi-platform scraping, AI qualification triage, tracking, and tailored application generation framework
metadata:
  opencode/autoinvoke: true
---

# Job Search & Application Pipeline Skill

This skill provides a complete, reusable operational framework for automating the entire career search lifecycle. It covers multi-platform automated scraping, AI qualification evaluation, database tracking, rapid interactive triage, and tailored ATS-optimized application generation (Markdown + Word `.docx`).

---

## 🏗️ Architecture Overview

The pipeline operates on a decoupled two-stage architecture:

```
[ Automated Nightly Pipeline (Systemd / Cron / Windows Task Scheduler @ 2:00 AM) ]
       │
       ▼
[ Stage 1: Ingestion (`scripts/job_scraper.py`) ]
   • Aggregates listings across Indeed, LinkedIn, ZipRecruiter, and Glassdoor using `python-jobspy`.
   • Performs basic hygiene (filters expired links, deduplicates against existing database).
   • Appends new listings to `tracking.csv` with `Status: Unscreened`.
       │
       ▼
[ Stage 2: AI Triage Agent (`scripts/ai_triage.py`) ]
   • Reads all newly added `Unscreened` listings.
   • Loads candidate context dynamically from `base_resume.md` and `criteria.md`.
   • Evaluates jobs in batches (25 jobs per LLM request) to conserve token quota.
   • Assigns a 0–100 Qualification Score and 1-sentence rationale:
       - Score >= 70 ➔ Promoted to `Status: Pending` (ready for morning review).
       - Score < 70 ➔ Marked `Status: Skipped` with rationale recorded in `Notes`.
       │
       ▼
[ Interactive Morning Review (Agent Pair Programming) ]
   • Candidate and AI review only pre-vetted, high-conviction jobs (`Status == 'Pending'`).
   • Quick "Proceed" or "Pass" triage per job.
   • For "Proceed" jobs, AI generates tailored resumes and cover letters in `applications/`.
   • Tracks all submissions in `tracking.csv` as `Status: Applied`.
```

---

## 📁 Workspace Structure

When instantiating this skill in a project workspace, initialize the following structure:

```text
my-job-search/
├── base_resume.md              # Master source-of-truth resume (all skills, career history, metrics)
├── criteria.md                 # Target roles, tech keywords, salary targets, and disqualifiers
├── tracking.csv                # Central database: Company, Role, Link, Date Posted, Date Applied, Status, Notes
├── applications/               # Directory where tailored resumes and cover letters are stored
├── scripts/
│   ├── job_scraper.py         # Multi-platform job aggregator
│   ├── ai_triage.py           # Batched LLM qualification evaluator
│   └── document_compiler.py   # Markdown to .docx conversion script (pypandoc)
└── templates/                  # Reference templates provided by this skill
    ├── base_resume.template.md
    ├── criteria.template.md
    ├── master_cover_letter.template.md
    ├── tracking.template.csv
    ├── job-pipeline.service.template
    ├── job-pipeline.timer.template
    ├── run-job-pipeline.ps1.template
    └── register-windows-task.ps1.template
```

---

## 🚀 Setup & Initialization Workflow

When a new user imports this skill, guide them through the following setup steps:

### Step 1: Environment & Dependencies
Create a dedicated Python virtual environment and install required packages:

**Linux / macOS (Bash):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install python-jobspy pandas pypandoc markdown beautifulsoup4 requests
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install python-jobspy pandas pypandoc markdown beautifulsoup4 requests
```

### Step 2: Establish Source-of-Truth Profile Files
1. Copy `templates/criteria.template.md` to `criteria.md` and customize:
   * Target role titles (primary and adjacent).
   * Desired compensation floor and target range.
   * Target tech stack and protocols.
   * Hard disqualifiers (e.g., clearance requirements, specific licenses, over-seniority ceilings).
2. Copy `templates/base_resume.template.md` to `base_resume.md` and populate:
   * Full comprehensive career history.
   * Specific quantifiable achievements and metrics (e.g., cost savings, efficiency gains, team size).
   * Key project deliverables that substantiate senior compensation.
3. Initialize `tracking.csv` using `templates/tracking.template.csv`.
4. Create the `applications/` output folder:
   * **Linux / macOS:** `mkdir -p applications`
   * **Windows (PowerShell):** `New-Item -ItemType Directory -Force -Path applications`

### Step 3: Configure Scripts
* Copy `scripts/job_scraper.py` and customize `SEARCH_QUERIES`, `SEARCH_LOCATIONS`, and lookback hours (`HOURS_LOOKBACK = 72` or `168`).
* Copy `scripts/ai_triage.py` to the project root or `scripts/` directory.
* Set `TRIAGE_BACKEND` if not using the default `opencode` CLI: supported values are `opencode`, `claude`, `codex`, and `openai` (which uses `OPENAI_API_KEY`, plus optional `OPENAI_MODEL` and `OPENAI_BASE_URL`).

---

## 🤖 AI Triage Agent: Evaluation Rules & Prompting

The AI evaluation agent (`scripts/ai_triage.py`) enforces strict qualification filtering to eliminate clutter while maintaining cross-industry mobility:

1. **Capability Over Industry:** The candidate is open to multiple sectors where their technical skills translate. Do not disqualify a job simply because it is in an adjacent industry if core technical proficiencies align.
2. **Seniority Ceiling Gate:** Automatically reject (Score < 50) titles demanding 10–15+ years of executive pedigree (Director, VP, Principal, Staff, Head of, Chief) unless the user specifically targets executive tiers.
3. **Unqualified Domain Silos:** Automatically reject (Score < 50) specialized domains requiring years of non-overlapping expertise (e.g., corporate accounting/FinOps, specialized threat hunting, core hardware engineering, or licensed clinical roles).
4. **Hard Disqualifiers:** Reject any position demanding active clearances or state licenses that the candidate does not hold.
5. **Score Threshold:**
   * **Score >= 70:** Promoted to `Pending` for human review.
   * **Score < 70:** Marked `Skipped` with a concise 1-sentence rationale logged in `Notes`.

---

## 📝 Application Tailoring & Generation SOP

When the user reviews a `Pending` listing and chooses to **Proceed**, execute this exact procedure:

1. **Scrape or Review the Target JD:**
   * Fetch the full job description from the listing URL (or prompt the user to paste it if blocked by anti-bot protections).
   * Identify core technical priorities, required frameworks, and terminology used by the hiring team.
2. **Tailor the Resume:**
   * Cross-reference the JD against `base_resume.md` and `criteria.md`.
   * **Title Alignment:** Update the header headline to match the target position title.
   * **Years of Experience Upfront:** State years of experience directly in the opening sentence of the summary.
   * **Bold Skim-Headers:** Begin every single experience bullet with a **Bold Phrase Header:** (e.g., **Infrastructure Automation:**, **Interface Engineering:**) for rapid scanning.
   * **Preserve Quantifiable Metrics:** Retain all hard dollar amounts, performance percentages, and architectural metrics from `base_resume.md`.
   * **Mandatory Projects:** Keep 2 distinct technical deliverables in a *Key Projects & Technical Deliverables* section to justify senior compensation bands.
3. **Cover Letters (Strict Protocol):**
   * **Do NOT generate a cover letter unless the user explicitly requests one.**
   * When requested, adapt `templates/master_cover_letter.template.md`.
   * **Header Rule:** Never include the company's physical street address or location in the header block (only Candidate Info, Date, Hiring Team / Company Name, and the Re: line).
4. **File Naming & Compilation:**
   * Save Markdown source to: `applications/Candidate_Name_<EmployerName>_Resume.md`
   * Compile to Word document using `scripts/document_compiler.py`:
     ```bash
     python scripts/document_compiler.py applications/Candidate_Name_<EmployerName>_Resume.md
     ```
   * Result: A cleanly formatted, native `.docx` with standard bulleted indentation that parses cleanly through any enterprise ATS.
5. **Update Tracker:**
   * Update the job row in `tracking.csv`:
     * `Status` = `Applied`
     * `Date Applied` = Current Date (`YYYY-MM-DD`)
     * `Notes` = Append tailoring notes / position details.

---

## ⚙️ Scheduling Automation (Systemd / Cron / Windows Task Scheduler)

To run the pipeline hands-free nightly at 2:00 AM:

### Linux (Systemd)
1. Copy `templates/job-pipeline.service.template` to `~/.config/systemd/user/job-pipeline.service` and replace paths.
2. Copy `templates/job-pipeline.timer.template` to `~/.config/systemd/user/job-pipeline.timer`.
3. Enable and start the timer:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now job-pipeline.timer
   ```
4. Check status:
   ```bash
   systemctl --user list-timers
   ```

### Windows (Task Scheduler)
1. Copy `templates/run-job-pipeline.ps1.template` to `run-job-pipeline.ps1` in your workspace and update `$WorkspaceDir`.
2. Copy `templates/register-windows-task.ps1.template` to `register-windows-task.ps1`, update `$ScriptPath`, and run it in PowerShell:
   ```powershell
   .\register-windows-task.ps1
   ```
3. Check status:
   ```powershell
   Get-ScheduledTask -TaskName JobSearchPipeline
   ```

---

## 💡 Best Practices for Users
* **Do Not Settle on Early Counter-Offers:** When an employer makes an initial offer, evaluate total realized compensation (base salary + verified 401(k) match + annual bonus potential) rather than base pay alone.
* **Verify 401(k) via DOL Form 5500:** Always verify whether an employer's advertised 401(k) match is real by checking public Department of Labor Form 5500 filings before using it in compensation comparisons.
* **Maintain the Base Resume:** Treat `base_resume.md` as an exhaustive career repository. The more specific projects, metrics, and technologies documented there, the higher the AI triage scoring accuracy will be.
