#!/usr/bin/env python3
"""
ai_triage.py (Template)
Autonomous AI Evaluation Agent for job listings.
Reads 'Unscreened' or 'Pending' listings from tracking.csv, evaluates them
in batches against base_resume.md and criteria.md, scores candidate qualification
from 0 to 100, and updates tracking.csv.
"""

import json
import os
import sys
import shutil
import subprocess
import re
import time
import urllib.request
import urllib.error
import pandas as pd

# --- CONFIGURATION (Adjust relative or absolute paths as needed) ---
CSV_FILE = "tracking.csv"
BASE_RESUME_FILE = "base_resume.md"
CRITERIA_FILE = "criteria.md"
MIN_FIT_SCORE = 70
BATCH_SIZE = 25

# Supported backends: "opencode" (default), "claude", "codex", "openai"
TRIAGE_BACKEND = os.environ.get("TRIAGE_BACKEND", "opencode").strip().lower()
OPENCODE_BIN = os.environ.get("OPENCODE_BIN", "opencode")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
CODEX_BIN = os.environ.get("CODEX_BIN", "codex")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")

def load_context():
    """Loads base resume and search criteria for LLM evaluation."""
    resume_text = ""
    criteria_text = ""
    if os.path.exists(BASE_RESUME_FILE):
        with open(BASE_RESUME_FILE, "r", encoding="utf-8") as f:
            resume_text = f.read()
    else:
        print(f"Warning: {BASE_RESUME_FILE} not found. Please create it from template.")

    if os.path.exists(CRITERIA_FILE):
        with open(CRITERIA_FILE, "r", encoding="utf-8") as f:
            criteria_text = f.read()
    else:
        print(f"Warning: {CRITERIA_FILE} not found. Please create it from template.")

    return resume_text, criteria_text

def build_batch_prompt(jobs_batch, resume_text, criteria_text):
    """Constructs a structured multi-job qualification prompt."""
    jobs_formatted = []
    for item in jobs_batch:
        jobs_formatted.append(f"""ID: {item['index']}
Company: {item['company']}
Title: {item['role']}
Notes: {item['notes']}""")
        
    jobs_text = "\n---\n".join(jobs_formatted)

    return f"""You are an expert technical talent evaluator and recruiter evaluating job opportunities for a candidate.
Evaluate each of the following {len(jobs_batch)} job opportunities and determine if the candidate is genuinely qualified.

### CANDIDATE RESUME & EXPERTISE:
{resume_text}

### CANDIDATE TARGET CRITERIA & GOALS:
{criteria_text}

### EVALUATION RULES:
1. CAPABILITY OVER DOMAIN: The candidate is open to multiple technical sectors where their skills translate. Do NOT reject a job solely because it is in an adjacent industry if their core skills match.
2. OVER-SENIORITY CEILING: Reject (Score < 50) if the title demands 10-15+ years of dedicated executive pedigree (e.g., Director, VP, Principal, Head of, Chief, Distinguished).
3. UNQUALIFIED SILOS: Reject (Score < 50) if the role is a specialized non-systems silo outside their qualifications (e.g., dedicated corporate accounting/FinOps, pure military hardware, framework coding from scratch in languages they lack, or licensed clinical roles).
4. CLEARANCES: Reject (Score < 40) if it requires an active government security clearance they do not hold.
5. QUALIFIED FIT (Score >= 70): Award 70-100 if the role aligns with their verified technical proficiencies, architectures, and systems experience.

### JOBS TO EVALUATE:
{jobs_text}

Respond ONLY with a valid JSON array of objects in this exact format (no markdown formatting, no code blocks, no backticks):
[
  {{"id": <integer id>, "fit_score": <integer 0-100>, "verdict": "Proceed" or "Skip", "rationale": "<concise 1-sentence explanation>"}},
  ...
]"""

def _query_openai_api(prompt):
    """Executes a prompt using the OpenAI Chat Completions REST API."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required when TRIAGE_BACKEND=openai.")

    payload = json.dumps({
        "model": os.environ.get("OPENAI_MODEL", OPENAI_MODEL),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }).encode("utf-8")

    req = urllib.request.Request(
        os.environ.get("OPENAI_BASE_URL", OPENAI_BASE_URL),
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error (HTTP {e.code}): {err_body[:300]}") from e

    return data["choices"][0]["message"]["content"].strip()

def query_llm_batch(prompt):
    """Executes a prompt using the configured LLM backend (opencode, claude, codex, or openai)."""
    backend = os.environ.get("TRIAGE_BACKEND", TRIAGE_BACKEND).strip().lower()

    if backend == "openai":
        raw_output = _query_openai_api(prompt)
    else:
        cli_map = {
            "opencode": (os.environ.get("OPENCODE_BIN", OPENCODE_BIN), ["run"]),
            "claude": (os.environ.get("CLAUDE_BIN", CLAUDE_BIN), ["-p"]),
            "codex": (os.environ.get("CODEX_BIN", CODEX_BIN), ["exec", "-"]),
        }
        if backend not in cli_map:
            raise ValueError(
                f"Unsupported TRIAGE_BACKEND '{backend}'. Expected one of: opencode, claude, codex, openai."
            )
        bin_name, args = cli_map[backend]
        resolved_bin = shutil.which(bin_name) or bin_name
        cmd = [resolved_bin, *args]
        res = subprocess.run(
            cmd,
            input=prompt,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        if res.returncode != 0:
            raise RuntimeError(f"{backend} execution error (code {res.returncode}): {res.stderr}")

        raw_output = res.stdout.strip()

    json_match = re.search(r"\[[\s\S]*\]", raw_output)
    if not json_match:
        raise ValueError(f"No JSON array found in output: {raw_output[:200]}")

    return json.loads(json_match.group(0))

def run_triage(target_status="Unscreened", batch_size=BATCH_SIZE):
    """Processes jobs matching target_status in batches and updates tracking.csv."""
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    resume_text, criteria_text = load_context()
    df = pd.read_csv(CSV_FILE, encoding="utf-8")

    pending_indices = list(df[df["Status"] == target_status].index)
    total_jobs = len(pending_indices)

    if total_jobs == 0:
        print(f"No jobs found with Status == '{target_status}'. Nothing to triage.")
        return

    total_batches = (total_jobs + batch_size - 1) // batch_size
    print(f"=== STARTING AI TRIAGE RUN ===")
    print(f"Target Status: {target_status} | Total Jobs: {total_jobs}")
    print(f"Batch Size: {batch_size} ({total_batches} batches)")

    promoted_total = 0
    skipped_total = 0

    for batch_num in range(total_batches):
        batch_idx_slice = pending_indices[batch_num * batch_size : (batch_num + 1) * batch_size]
        jobs_batch = []
        for idx in batch_idx_slice:
            jobs_batch.append({
                "index": int(idx),
                "company": str(df.loc[idx, "Company"]) if pd.notnull(df.loc[idx, "Company"]) else "Unknown Company",
                "role": str(df.loc[idx, "Role"]) if pd.notnull(df.loc[idx, "Role"]) else "Unknown Role",
                "notes": str(df.loc[idx, "Notes"]) if pd.notnull(df.loc[idx, "Notes"]) else ""
            })

        print(f"\n[Batch {batch_num + 1}/{total_batches}] Processing {len(jobs_batch)} jobs...")
        
        retries = 3
        results = None
        while retries > 0:
            try:
                t0 = time.time()
                prompt = build_batch_prompt(jobs_batch, resume_text, criteria_text)
                results = query_llm_batch(prompt)
                elapsed = time.time() - t0
                print(f"  -> Batch evaluated in {elapsed:.2f}s")
                break
            except Exception as e:
                retries -= 1
                print(f"  -> Warning: {e}. Retrying ({retries} left)...")
                time.sleep(3)

        if not results:
            print(f"  -> Skipping batch {batch_num + 1} due to error.")
            continue

        for res in results:
            job_id = res.get("id")
            score = res.get("fit_score", 0)
            rationale = res.get("rationale", "")

            if job_id in df.index:
                orig_notes = str(df.loc[job_id, "Notes"]) if pd.notnull(df.loc[job_id, "Notes"]) else ""
                clean_orig_notes = orig_notes.split(" | AI-")[0]
                if score >= MIN_FIT_SCORE:
                    df.loc[job_id, "Status"] = "Pending"
                    df.loc[job_id, "Notes"] = f"{clean_orig_notes} | AI-Score: {score}/100: {rationale}".strip(" |")
                    promoted_total += 1
                else:
                    df.loc[job_id, "Status"] = "Skipped"
                    df.loc[job_id, "Notes"] = f"{clean_orig_notes} | AI-Skipped: ({score}/100): {rationale}".strip(" |")
                    skipped_total += 1

        # Save progress after every batch
        df.to_csv(CSV_FILE, index=False, encoding="utf-8")
        print(f"  -> Progress saved: {promoted_total} Qualified (>=70), {skipped_total} Skipped (<70)")

    print("\n==========================================")
    print(f"AI TRIAGE COMPLETE:")
    print(f"Total Qualified (Promoted to 'Pending'): {promoted_total}")
    print(f"Total Disqualified (Marked 'Skipped'): {skipped_total}")
    print(f"Current Pending Total: {(df['Status'] == 'Pending').sum()}")

if __name__ == "__main__":
    status_target = sys.argv[1] if len(sys.argv) > 1 else "Unscreened"
    batch_sz = int(sys.argv[2]) if len(sys.argv) > 2 else BATCH_SIZE
    run_triage(target_status=status_target, batch_size=batch_sz)
