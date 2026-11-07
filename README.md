WorkDone – Technical Recruitment & Hiring Portal
WorkDone is a beginner-friendly recruitment portal for technical jobs. It provides separate spaces for applicants and invited hiring board members.
Features
Applicant
Register and log in
Add education, work experience and technical skills
Browse technical job openings and apply
Track application status
View online or offline interview invitations
Hiring board
Board-member registration protected by an invitation code
Publish technical job openings
Review applicant profiles and contact details
Shortlist, reject or update applications
Schedule online or offline interviews and provide meeting details
General
Home, About, Contact and Support pages
Responsive layout for desktop and mobile
SQLite database
Technology
Frontend: HTML, CSS, JavaScript
Backend: Python and Flask
Database: SQLite
Run locally (Windows)
Install Python 3.10 or newer.
Download or clone this repository.
Open the project folder in VS Code.
Open a terminal and run:
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
If PowerShell blocks activation, use Command Prompt and run:
.venv\Scripts\activate.bat
Set a private invitation code for board registration:
$env:WORKDONE_BOARD_INVITE="Choose-A-Private-Code"
$env:WORKDONE_SECRET="Use-A-Long-Random-Secret"
Start the app:
py app.py
Open http://127.0.0.1:5000 in your browser.
The local SQLite database (workdone.db) is created automatically. It is intentionally excluded from Git using .gitignore.
GitHub upload using Git
Create an empty repository on GitHub named WorkDone. Then, from the project folder, run:
git init
git add .
git commit -m "Initial WorkDone recruitment portal"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/WorkDone.git
git push -u origin main
Replace YOUR-USERNAME with your GitHub username.
Important security and deployment notes
This is an educational starter project, not a production-ready recruitment service. Do not publish real applicant data, passwords, invitation codes, secret keys or the local database.
Before public deployment, add CSRF protection, rate limiting, email verification, password reset, stronger input validation, audit logging, HTTPS, secure production configuration, backups, privacy/consent notices and data-retention controls. Turn off Flask debug mode in production.
The contact form currently saves messages in the local database; it does not send email. Online interview details are entered by board members; the app does not create video meetings automatically. Resume upload and automated notifications are not included yet.