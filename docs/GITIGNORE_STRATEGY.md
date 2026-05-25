# Gitignore Strategy & Repository Security

## Overview
This document explains the security model for the Hour-Zero repository, specifically what is excluded from version control to prevent credential leaks during our "Build in Public" journey.

## 🛡️ Excluded Files (The "Invisible" Layer)

### 1. `.env` (Environment Variables)
*   **Why:** Contains the `META_ACCESS_TOKEN`, `SUPABASE_DB_URL`, and other sensitive keys.
*   **Action:** Never commit this file. Always use `.env.example` as a template for new environments.

### 2. `service-account.json` (GCP Credentials)
*   **Why:** Provides full programmatic access to your Google Cloud Project.
*   **Action:** In this Codespace, we use `gcloud auth login` for interactive access, but if a service account key is generated, it is explicitly ignored.

### 3. `__pycache__/` and Python Artifacts
*   **Why:** Compiled Python files and local environment folders (`venv/`) are specific to your machine/Codespace.
*   **Action:** Ignored to keep the repository clean and portable.

## 🚀 Public Repository Best Practices
When pushing to a public repository:
1. **Audit Logs:** Periodically check your Git history to ensure no secrets were accidentally committed and then deleted (they still exist in history).
2. **Rotate Keys:** If you ever suspect a leak, regenerate your Meta Token and Supabase password immediately.
3. **Secret Scanning:** GitHub will automatically notify you if it detects a known secret pattern (like a Meta or Google key) in your code. Take these alerts seriously.

## 🔒 Codespace Security
The Codespace serves as a "Secure Enclave." While the code is pushed to GitHub, the actual `.env` file and authenticated `gcloud` session exist only within the secure lifecycle of this environment.
