AutoExam AI
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
Use this guide
Start with the local website. The Python grading and MySQL sections can be run independently from their own package folders.
Local setup
1. Download AutoExam-All-Folders.zip.
2. Extract it to a writable folder.
3. Open AutoExam-Website-Server-40.
4. Find app.py, backend/, and frontend/.
5. Open a terminal in that folder.
6. Run python --version.
7. Use Python 3.10 or later.
8. For optional Flask, install requirements with python -m pip install -r requirements.txt.
9. Start the server with python app.py.
10. On Windows, run.bat can also start it.
11. Wait for the startup message.
12. Open http://127.0.0.1:8000.
13. Find the demo sign-in details in the terminal.
14. Check that the sign-in page loads.
15. Keep the terminal open while using the site.
Prepare a repeatable demo
16. Choose an exam topic with clear reference answers.
17. Use demo accounts and sample answers for the walkthrough.
18. Decide whether you need a timed, proctored exam or a simpler grading demonstration.
19. Plan a short paper with one objective question and one descriptive question.
20. Write the expected answer for each item before adding it to the bank.
21. Decide what earns full, partial, and zero marks on the descriptive item.
22. Keep a sample correct response and a sample incomplete response for comparison.
23. Choose a published and unrestricted exam for the quickest student walkthrough.
24. Use a separate restricted exam when demonstrating assignments.
25. Keep the server on localhost while using the bundled demo accounts.
Question bank
26. Sign in with the faculty demo account.
27. Open Exams & Question Bank.
28. Open the question bank.
29. Choose the option to add a question.
30. Select the question type.
31. Enter a subject such as Python.
32. Pick a difficulty level.
33. Write a clear question prompt.
34. Set the maximum marks.
35. For multiple choice, add options and select the correct one.
36. For true/false, select the expected answer.
37. For short or descriptive answers, write a reference answer.
38. Add rubric keywords for short or descriptive answers.
39. For programming, supply the reference source text.
40. Save the item and find it in the question list.
Build and publish an exam
41. Return to Exams & Question Bank.
42. Choose Create exam.
43. Enter the exam title and subject.
44. Write a short description for students.
45. Set the duration in minutes.
46. Set the passing percentage.
47. Choose whether to enable proctoring.
48. Set the warning limit if proctoring is enabled.
49. Choose whether to restrict access to assigned students.
50. Set opening and closing times if needed.
51. Choose manual entry, question-bank selection, or random generation.
52. For random generation, set the filters and paper size.
53. Save the exam as a draft.
54. Preview the paper and check its order and marks.
55. Publish the exam when it is ready.
Check the exam before students start
56. Check that each question prompt states what the student must provide.
57. Verify that each multiple-choice key matches its intended option.
58. Preview the answer choices in the order students will see them.
59. Check that descriptive questions use reference answers and relevant keywords.
60. Confirm that the total marks match the planned paper.
61. Compare the exam duration with the expected time for the questions.
62. Review scheduled times in the browser's local timezone.
63. Confirm that the exam has the intended published status.
64. If the exam is restricted, assign it from the admin portal.
65. Sign in as the assigned student to confirm that the exam is visible.
Take the exam
66. Sign out of the faculty account.
67. Sign in with the student demo account.
68. Open Available Exams.
69. Select a published exam you can access.
70. Check the scheduled opening time if you cannot start.
71. Read the exam instructions.
72. Complete any pre-exam readiness checks.
73. Grant camera permission if the exam requires it.
74. Start the attempt and check the timer.
75. Select answers for the objective questions.
76. Type responses for the descriptive questions.
77. Enter source text for any programming question.
78. Use the question navigator to revisit unanswered items.
79. Submit before the timer expires.
80. Open My Results & AI Feedback when faculty publish the grade.
Review and publish grades
81. Sign in again as faculty.
82. Open Submissions & AI Review.
83. Find the exam and the submitted attempt.
84. Open the attempt to see the answer breakdown.
85. Compare objective marks with the answer key.
86. Compare text responses with reference answers.
87. Read the grading feedback.
88. Inspect the responses marked for review.
89. Open the recorded proctoring events if available.
90. Treat an event as a review signal and check its context.
91. Enter a mark override if the rubric warrants it.
92. Record a faculty comment that explains the decision.
93. Check the updated total and percentage.
94. Publish the reviewed result.
95. Open Performance Analytics to review results or export a CSV.
Test the grading workflow
96. Use separate demo attempts when comparing different responses.
97. Submit a correct objective answer and compare the awarded marks with the key.
98. Submit a wrong objective answer in a different demo attempt for comparison.
99. Try a descriptive answer that expresses the reference concept in different words.
100. Try an incomplete answer and compare its feedback with the complete answer.
101. Open the faculty attempt details and check which responses need review.
102. For a programming answer, compare submitted source text with the reference text. The evaluator does not execute student code.
103. For a proctored demo attempt, switch tabs once and check the recorded visibility event.
104. Verify that a faculty adjustment updates the displayed overall result.
105. After publication, confirm that the student sees the reviewed grade.
Administration and verification
106. Sign in with the admin demo account.
107. Open User & Role Management.
108. Check the available student and faculty accounts.
109. Open Subjects to manage the subject list.
110. Open Exam Assignments for a restricted exam.
111. Choose the exam and student.
112. Save the assignment and verify student access.
113. Open Audit Trail to review recorded activity.
114. Inspect System Analytics for overall activity.
115. Locate the demo database at data/exam_system.db.
116. Run python -m unittest discover -s tests -v from the server folder.
117. If port 8000 is busy, set EXAM_PORT to another port and restart.
118. Open the address printed in the terminal.
119. Stop the local server with Ctrl+C when you finish.
120. Read the server README before changing the database or launch settings.
Follow the website source
121. Open app.py to find the server launcher and demo sign-in information.
122. Open backend/config.py to find the host, port, and database settings.
123. Open backend/router.py to follow routes in the built-in HTTP server.
124. Open backend/flask_app.py to locate the Flask implementation.
125. Read backend/database.py to see how the SQLite schema and demo records are created.
126. Read backend/exam_service.py to follow attempt creation, submission, and review.
127. Read backend/nlp_evaluator.py to trace the built-in grading logic.
128. Read backend/cv_proctor.py to see how monitoring events contribute to integrity summaries.
129. Open frontend/js/cv-proctor.js to trace browser-side monitoring.
130. Compare the standalone ML demo with the grading flow used by the running website.
Python machine-learning demo
131. Open a terminal in AutoExam-Python-34.
132. Read the package README for the full training command.
133. Open data/train.jsonl to see the labeled answer format.
134. Check data/validation.jsonl for held-out questions.
135. Keep data/test.jsonl separate for final evaluation.
136. Use audit_data to check for question overlap.
137. Run the training command to regenerate artifacts/model.json.
138. Open artifacts/metrics.json to review validation error.
139. Score data/example.json with the score command in the README.
140. Read the suggested marks and the review flag.
141. Use inspect_features to see the signals behind a prediction.
142. Use batch_score for a JSON array of answer records.
143. Use review_queue to export flagged batch results.
144. Run the evaluate command on data/test.jsonl.
145. Use these synthetic-data results to demonstrate the workflow.
Run the Python grading commands
146. From AutoExam-Python-34, run python -m autoexam_ml --help to list the core commands.
147. Run python -m autoexam_ml audit_data data/train.jsonl data/validation.jsonl data/test.jsonl to check split overlap.
148. Run python -m autoexam_ml dataset_summary data/train.jsonl to inspect training questions and labels.
149. Run python -m autoexam_ml train data/train.jsonl data/validation.jsonl artifacts/model.json artifacts/metrics.json to train the demo model.
150. Run python -m autoexam_ml inspect_model artifacts/model.json to list the feature coefficients.
151. Run python -m autoexam_ml inspect_features data/example.json to see the features for one answer.
152. Run python -m autoexam_ml score artifacts/model.json data/example.json to score that answer.
153. Run python -m autoexam_ml evaluate artifacts/model.json data/test.jsonl to check held-out performance.
154. Run python -m autoexam_ml error_report artifacts/model.json data/test.jsonl errors.json for answer-level errors.
155. Run python -m unittest discover -s tests -v from the Python package to test the grading utilities.
Frontend files and MySQL
156. Open AutoExam-JavaScript-34 to browse 34 JavaScript modules.
157. Read frontend/js/app.js for portal navigation.
158. Read frontend/js/api.js for how requests and sessions work.
159. Open AutoExam-HTML-CSS-34 for one HTML page and 33 CSS files.
160. Read frontend/index.html to find the page entry point.
161. Open frontend/css/styles.css to see the stylesheet order.
162. Open AutoExam-ML-34 for the smaller grading demo.
163. Open AutoExam-MySQL-34 for the 34 SQL scripts.
164. Start a MySQL 8.0.16+ client connected to a MySQL server.
165. Enter SOURCE 00_install.sql; from the MySQL package folder.
166. Run SHOW TABLES; to inspect the installed database.
167. Optionally load SOURCE 33_demo_subjects.sql;.
168. Run a report numbered 19 to 28.
169. Run a check numbered 29 to 32. Healthy checks return zero rows.
170. Use the website's SQLite database for the default demo.
Inspect the MySQL database
171. Open the terminal in AutoExam-MySQL-34 so the installer can find its script files.
172. Use a MySQL account with permission to create the demo database, tables, and views.
173. Connect with mysql -u YOUR_USER -p --abort-source-on-error.
174. After installation, run USE autoexam; in the MySQL client.
175. Run SHOW CREATE TABLE answers; to examine the answer table and its keys.
176. Run SHOW CREATE TABLE exam_attempts; to inspect attempt status and scoring fields.
177. Run SHOW FULL TABLES WHERE Table_type = 'VIEW'; to list the installed views.
178. If you loaded the sample subjects, run SELECT code, name FROM subjects ORDER BY code; to confirm the rows.
179. Read a report script before running it so you know which records it expects. Exam reports can be empty on a fresh schema.
180. Exit the client with QUIT; when you finish.
Troubleshoot the local demo
181. If Python is missing, install Python 3.10 or newer and reopen the terminal.
182. If app.py cannot be found, check that the terminal is inside AutoExam-Website-Server-40.
183. If port 8000 is occupied, set $env:EXAM_PORT = '8080' in PowerShell before restarting.
184. When using port 8080, open http://127.0.0.1:8080 instead of the default address.
185. If the browser cannot connect, confirm that the server process is still running and read its terminal output.
186. If a student cannot see a restricted exam, verify its assignment and publication status.
187. If a proctored attempt cannot access the camera, inspect the browser permission for the local site.
188. If a result is missing from the student portal, check that faculty published that attempt.
189. If an ML command cannot find data files, run it from the Python package folder.
190. If MySQL SOURCE cannot find a file, check the terminal's working directory and the full script filename.
