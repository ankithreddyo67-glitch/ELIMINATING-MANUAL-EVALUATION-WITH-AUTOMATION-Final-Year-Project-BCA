utoExam AI
Eliminating Manual Evaluation with Automation is a BCA final-year project for creating online exams, scoring submissions, and reviewing results. Students take exams, faculty manage questions and review grades, and administrators manage users and assignments.
Package map
Folder	Files	Purpose
AutoExam-Website-Server-40	40 files total	Runnable website, Python server, and tests
AutoExam-JavaScript-34	34 JavaScript files	Browser logic for the student, faculty, and admin portals
AutoExam-Python-34	34 Python files	Model training, batch scoring, and evaluation utilities
AutoExam-MySQL-34	34 SQL files	Separate MySQL schema, reports, and integrity checks
AutoExam-HTML-CSS-34	1 HTML page and 33 CSS files	Page structure, themes, layout, and print styles
AutoExam-ML-34	34 files total	Grading demo with synthetic data and a trained model


The website runs on SQLite by default. The MySQL scripts create a separate database. The standalone ML model can be tried independently of the website's built-in evaluator.
Start the website
1. Extract AutoExam-All-Folders.zip and open the extracted folder.
2. Check your Python version with python --version. Use Python 3.10 or newer.
3. Open a terminal in AutoExam-Website-Server-40. This folder contains app.py, backend/, and frontend/.
4. To use Flask, run python -m pip install -r requirements.txt. The launcher can also use Python's built-in HTTP server.
5. Run python app.py. On Windows, run.bat is another launch option.
6. Open http://127.0.0.1:8000. The first run creates a demo SQLite database, and the terminal prints the demo sign-in credentials.
Create an exam as faculty
7. Sign in using the faculty demo account.
8. Choose Exams & Question Bank, then open the question bank.
9. Add a question with a subject, difficulty, maximum marks, and a reference answer. The supported types include multiple choice, true/false, short answer, descriptive, and programming.
10. For a descriptive question, enter rubric keywords that identify the concepts you expect in the answer.
11. Choose Create exam. Set the exam title, duration, passing percentage, and any proctoring settings.
12. Write questions directly, select questions from the bank, or generate a paper from matching bank questions.
13. Save the exam as a draft, check the questions and marks, and publish when the paper is ready.
Take an exam as a student
14. Sign out and use the student demo account.
15. Open Available Exams and select a published exam. Restricted exams require an assignment.
16. Complete any pre-exam checks shown. Grant camera permission if the selected exam requires it.
17. Answer the questions and submit before the timer expires. For a demo of the visibility warning, you can switch tabs during a proctored test attempt and then return to the exam.
18. Open My Results & AI Feedback after faculty publish the result.
Review grades and manage the system
19. Sign in as faculty and open Submissions & AI Review.
20. Open a submitted attempt to inspect the answers, provisional marks, feedback, and any recorded proctoring events.
21. Review flagged responses, enter any mark adjustments or remarks, and publish the result.
22. Open Performance Analytics to review exam results and use the available CSV export for a grade sheet.
23. Sign in as admin and open User & Role Management to inspect demo accounts and roles.
24. Use Subjects and Exam Assignments to manage subjects and assign a restricted exam to a student. Use Audit Trail to review recorded administrative activity.
Explore the source and run the other packages
25. Open frontend/index.html and frontend/css/styles.css in the HTML/CSS package to see how the browser loads the page and component styles.
26. Read frontend/js/app.js and frontend/js/api.js in the JavaScript package to follow portal navigation and API requests.
27. From AutoExam-Website-Server-40, run python -m unittest discover -s tests -v to check the backend, grading, and proctoring workflows.
28. Open a terminal in AutoExam-Python-34. Run python -m autoexam_ml audit_data data/train.jsonl data/validation.jsonl data/test.jsonl to check that the splits use different question IDs.
29. Train the descriptive-answer model with python -m autoexam_ml train data/train.jsonl data/validation.jsonl artifacts/model.json artifacts/metrics.json.
30. Score one sample with python -m autoexam_ml score artifacts/model.json data/example.json. Read the suggested marks and any review flag.
31. Evaluate the model with python -m autoexam_ml evaluate artifacts/model.json data/test.jsonl. The included data is synthetic, and faculty review is required before using the model for actual grades.
32. To try the separate MySQL package, open a terminal in AutoExam-MySQL-34 and start the MySQL 8 client with mysql -u YOUR_USER -p --abort-source-on-error.
33. In the MySQL client, run SOURCE 00_install.sql; and SHOW TABLES;. The installer creates the tables and views in dependency order.
34. Optionally run SOURCE 33_demo_subjects.sql;, then try a report numbered 19–28 and an integrity check numbered 29–32. A healthy integrity check returns zero rows.
