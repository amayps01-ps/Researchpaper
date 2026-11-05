# ResearchAI — Flask starter project

A beginner-friendly Flask application with registration, login, password reset email integration, SQLite storage, and a small TF-IDF/cosine-similarity paper recommender.

## Important project notes

- `papers` starts with 20 demonstration records. Some are real well-known papers; records marked "Demo dataset record" are illustrative. Verify every citation and add a larger verified dataset before academic submission.
- The recommender uses a small pure-Python TF-IDF + cosine similarity implementation. It is a demonstration, not a trained deep-learning model.
- Password reset email uses the Resend HTTPS API. A Resend account, API key, and verified sender domain are required for real email delivery.
- Never commit `.env`, API keys, Flask secret keys, or the live SQLite database to a public repository.
- This starter uses SQLite. It is appropriate for a small demo. For a larger public service with multiple app instances, use managed PostgreSQL.

## Run locally in VS Code

1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Create and activate a virtual environment:

   Windows PowerShell:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install packages:
   ```bash
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env`. Set a long random `SECRET_KEY`.
6. For email, add `RESEND_API_KEY` and `RESEND_FROM_EMAIL` from your Resend account. Set `APP_BASE_URL=http://127.0.0.1:5000` for local testing.
7. Start:
   ```bash
   python app.py
   ```
8. Open `http://127.0.0.1:5000`.

If email is not configured, registration/login/search still work, but forgot-password email will show a configuration error.

## Free public hosting: PythonAnywhere

PythonAnywhere is one simple option for a small Flask coursework demo. Free accounts currently have limits, including one web app, 512 MiB disk, 100 CPU seconds, and a one-month web-app expiry. Free accounts also have restricted outbound internet access. This means it is NOT a permanent always-on guarantee.

Official details:
- Free account limits: https://help.pythonanywhere.com/pages/FreeAccountsFeatures/
- Flask setup: https://help.pythonanywhere.com/pages/Flask
- Outbound internet allowlist: https://help.pythonanywhere.com/pages/403ForbiddenError
- Allowlist requests: https://help.pythonanywhere.com/pages/RequestingAllowlistAdditions

### Deploy on PythonAnywhere

1. Create a free account at https://www.pythonanywhere.com/ .
2. Open the **Web** tab, choose **Add a new web app**, select your `username.pythonanywhere.com` address, select **Flask**, and choose a Python version supported by the platform.
3. Upload this project folder to `/home/YOUR_USERNAME/ResearchAI_Free_Hosting` using the Files tab, or clone your GitHub repository into that location.
4. Open a Bash console and run:
   ```bash
   cd ~/ResearchAI_Free_Hosting
   python3 -m venv ~/.virtualenvs/researchai
   source ~/.virtualenvs/researchai/bin/activate
   pip install -r requirements.txt
   ```
5. In the **Web** tab, open the WSGI configuration file. Replace its contents with the following, after changing `YOUR_USERNAME`:
   ```python
   import sys
   project_home = '/home/YOUR_USERNAME/ResearchAI_Free_Hosting'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   from app import app as application
   ```
6. In the Web tab, set the virtualenv path to:
   `/home/YOUR_USERNAME/.virtualenvs/researchai`
7. Set environment variables in the Web app configuration or load them securely in your WSGI file. At minimum set:
   - `SECRET_KEY` to a long random secret
   - `APP_BASE_URL` to `https://YOUR_USERNAME.pythonanywhere.com`
   - `COOKIE_SECURE` to `1`
   - `RESEND_API_KEY` to your Resend API key
   - `RESEND_FROM_EMAIL` to a sender address verified in Resend
8. The free PythonAnywhere plan restricts outbound internet to an allowlist. Before expecting Resend to work, request allowlisting for `api.resend.com` using PythonAnywhere's official allowlist request process. If it is not allowed, password-reset email cannot reach Resend from the free account. Do not fall back to SMTP ports 465/587.
9. In the Web tab, click **Reload**.
10. Open `https://YOUR_USERNAME.pythonanywhere.com`.

### Important database persistence

The SQLite database is created in this project's `instance/researchai.sqlite3` folder. Keep this project directory in your persistent home directory. Do not delete the `instance` folder after users register. Back it up regularly.

## Security and production checklist

- Replace the development secret key with a long random secret.
- Keep environment variables out of Git.
- Use HTTPS.
- Configure a verified email sender.
- Add rate limiting and CSRF protection before opening registration/reset endpoints to broad public traffic.
- Add a larger verified academic dataset and source URLs/DOIs before presenting recommendations as real citations.
- Back up the database.
- Review provider limits and acceptable-use terms before sharing widely.
