import { apiFetch, escapeHtml, showToast } from "./api.js";
import { types, difficulties, choices, questionFields, readQuestion } from "./question-fields.js";
import { dialog, bindSubmit } from "./assessment-dialog.js";
import { scheduleFields, readSchedule } from "./exam-schedule.js";

export async function renderQuestionBank(container, back, initialBank) {
  const bank = initialBank ?? (await apiFetch("/api/question-bank")).questions;
  container.innerHTML = `
    <div class="topbar">
      <div><h1 class="page-title">Question Bank</h1><button class="btn btn-sm" id="bank-back">Back to exams</button></div>
      <button class="btn btn-primary" id="bank-add">Add question</button>
    </div>
    <section class="card">
      <div class="grid grid-3 assessment-controls">
        <label>Search questions<input id="bank-search" type="search"></label>
        <label>Subject<select id="bank-subject"><option value="">All subjects</option>
          ${[...new Set(bank.map((q) => q.subject))].map((subject) => `<option>${escapeHtml(subject)}</option>`).join("")}
        </select></label>
        <label>Difficulty<select id="bank-difficulty"><option value="">All levels</option>${choices(difficulties)}</select></label>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Question</th><th>Subject</th><th>Type</th><th>Difficulty</th><th>Marks</th><th>Actions</th></tr></thead>
        <tbody id="bank-rows"></tbody>
      </table></div>
    </section>`;
  const filters = ["search", "subject", "difficulty"].map((name) => container.querySelector(`#bank-${name}`));
  const rows = container.querySelector("#bank-rows");

  function draw() {
    const [search, subject, difficulty] = filters.map((input) => input.value);
    const filtered = bank.filter((q) =>
      (!subject || q.subject === subject) && (!difficulty || q.difficulty === difficulty)
      && q.prompt.toLowerCase().includes(search.trim().toLowerCase())
    );
    rows.innerHTML = filtered.map((q) => `
      <tr>
        <td>${escapeHtml(q.prompt)}</td><td>${escapeHtml(q.subject)}</td><td>${types[q.question_type]}</td>
        <td>${difficulties[q.difficulty]}</td><td>${q.max_marks}</td>
        <td><button class="btn btn-sm" data-edit="${q.id}">Edit</button>
            <button class="btn btn-sm btn-danger" data-delete="${q.id}">Delete</button></td>
      </tr>`).join("") || '<tr><td colspan="6">No matching questions.</td></tr>';
  }

  async function refresh() {
    const values = filters.map((input) => input.value);
    const next = await apiFetch("/api/question-bank");
    await renderQuestionBank(container, back, next.questions);
    filters.forEach((input, index) => {
      const current = container.querySelector(`#${input.id}`);
      if (current && values[index]) {
        current.value = values[index];
        current.dispatchEvent(new Event("input"));
      }
    });
  }

  function edit(question) {
    const modal = dialog(question ? "Edit question" : "Add question", `
      <form class="assessment-controls">
        <div data-fields></div>
        <button type="submit" class="btn btn-primary">Save question</button>
      </form>`);
    const fields = questionFields(question);
    modal.querySelector("[data-fields]").append(fields);
    bindSubmit(modal.querySelector("form"), async () => {
      const path = question ? `/api/question-bank/${question.id}` : "/api/question-bank";
      await apiFetch(path, { method: question ? "PATCH" : "POST", body: readQuestion(fields) });
      modal.close();
      await refresh();
    });
  }

  filters.forEach((input) => { input.oninput = draw; });
  container.querySelector("#bank-back").onclick = back;
  container.querySelector("#bank-add").onclick = () => edit();
  rows.onclick = async (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.edit) edit(bank.find((q) => q.id === Number(button.dataset.edit)));
    if (button.dataset.delete && window.confirm("Delete this question from your bank?")) {
      button.disabled = true;
      try {
        await apiFetch(`/api/question-bank/${button.dataset.delete}`, { method: "DELETE" });
        await refresh();
      } catch (error) {
        button.disabled = false;
        showToast(error.message, "error");
      }
    }
  };
  draw();
}

export async function showExamPaper(examId) {
  const { exam } = await apiFetch(`/api/exams/${examId}`);
  dialog(exam.title, `
    <ol class="paper-questions">${exam.questions.map((question) => `
      <li><strong>${escapeHtml(question.prompt)}</strong>
        <div>${types[question.question_type]} · ${escapeHtml(question.subject)} ·
          ${difficulties[question.difficulty]} · ${question.max_marks} marks</div>
        ${question.options.map((option) => `<div>${escapeHtml(option)}</div>`).join("")}
        <details><summary>Reference answer</summary><pre>${escapeHtml(question.model_answer)}</pre></details>
      </li>`).join("")}</ol>`);
}

function attachPaperEditor(form, items) {
  function addQuestion(question = { inline: true }) {
    const fields = questionFields(question);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn btn-sm btn-danger";
    remove.textContent = "Remove question";
    remove.onclick = () => fields.remove();
    const moveUp = document.createElement("button");
    moveUp.type = "button";
    moveUp.className = "btn btn-sm";
    moveUp.textContent = "Move up";
    moveUp.onclick = () => {
      if (fields.previousElementSibling) items.insertBefore(fields, fields.previousElementSibling);
    };
    const actions = document.createElement("div");
    actions.className = "assessment-actions";
    actions.append(moveUp, remove);
    fields.append(actions);
    items.append(fields);
  }
  form.querySelector("[data-add]").onclick = () => addQuestion();
  return addQuestion;
}

export async function editDraftPaper(examId, refresh) {
  const { exam } = await apiFetch(`/api/exams/${examId}`);
  const modal = dialog("Edit draft paper", `
    <form class="assessment-controls">
      <div data-items></div>
      <div class="assessment-actions">
        <button type="button" class="btn btn-sm" data-add>Add question</button>
        <button type="submit" class="btn btn-primary">Save paper</button>
      </div>
    </form>`);
  const form = modal.querySelector("form");
  const items = form.querySelector("[data-items]");
  const add = attachPaperEditor(form, items);
  exam.questions.forEach(add);
  bindSubmit(form, async () => {
    await apiFetch(`/api/exams/${examId}/paper`, {
      method: "PATCH", body: { questions: Array.from(items.children, readQuestion) },
    });
    modal.close();
    await refresh();
  });
}

export async function createExamDialog(refresh) {
  const { questions: bank } = await apiFetch("/api/question-bank");
  const modal = dialog("Create examination", `
    <form class="assessment-controls">
      <div class="grid grid-2">
        <label>Exam title<input name="title" minlength="3" required></label>
        <label>Exam subject<input name="subject" minlength="2" required></label>
      </div>
      <label>Description<input name="description"></label>
      <div class="grid grid-3">
        <label>Duration (minutes)<input type="number" name="duration_minutes" value="30" min="1" max="360" required></label>
        <label>Passing percentage<input type="number" name="passing_percentage" value="40" min="1" max="100" required></label>
        <label>Proctoring strictness<select name="proctoring_strictness">
          <option value="LOW">Low</option><option value="MEDIUM" selected>Medium</option><option value="HIGH">High</option>
        </select></label>
      </div>
      ${scheduleFields()}
      <label>Question source<select name="source">
        <option value="write">Write questions</option><option value="choose">Select from my bank</option>
        <option value="random">Generate from my bank</option>
      </select></label>
      <div data-source="write"><div data-items></div><button type="button" class="btn btn-sm" data-add>Add another question</button></div>
      <div data-source="choose" hidden>
        <label>Bank questions (hold Ctrl or Command to select multiple)
          <select name="bank_ids" multiple size="6">
            ${bank.map((question) => `<option value="${question.id}">
              ${escapeHtml(question.subject)} · ${difficulties[question.difficulty]} · ${escapeHtml(question.prompt)}
            </option>`).join("")}
          </select>
        </label>
      </div>
      <div class="grid grid-3" data-source="random" hidden>
        <label>Question count<input name="count" type="number" min="1" max="100" value="5" required></label>
        <label>Bank subject<select name="bank_subject"><option value="">Any subject</option>
          ${[...new Set(bank.map((q) => q.subject))].map((subject) => `<option>${escapeHtml(subject)}</option>`).join("")}
        </select></label>
        <label>Difficulty<select name="bank_difficulty"><option value="">Any difficulty</option>${choices(difficulties)}</select></label>
      </div>
      <label>Availability<select name="status"><option value="DRAFT">Save as draft</option><option value="PUBLISHED">Publish</option></select></label>
      <button type="submit" class="btn btn-primary">Create exam</button>
    </form>`);
  const form = modal.querySelector("form");
  const items = form.querySelector("[data-items]");
  const addQuestion = attachPaperEditor(form, items);
  const source = form.elements.source;
  function syncSource() {
    for (const section of form.querySelectorAll("[data-source]")) {
      section.hidden = section.dataset.source !== source.value;
      // A disabled fieldset keeps hidden question inputs out of browser validation.
      section.querySelectorAll(".question-fields").forEach((fields) => { fields.disabled = section.hidden; });
      if (section.dataset.source === "random") form.elements.count.disabled = section.hidden;
    }
  }
  source.onchange = syncSource;
  addQuestion();
  syncSource();

  bindSubmit(form, async () => {
    const data = new FormData(form);
    const body = {
      title: data.get("title"),
      subject: data.get("subject"),
      description: data.get("description"),
      proctoring_strictness: data.get("proctoring_strictness"),
      status: data.get("status"),
      ...readSchedule(data),
      duration_minutes: Number(data.get("duration_minutes")),
      passing_percentage: Number(data.get("passing_percentage")),
    };
    if (source.value === "write") body.questions = Array.from(items.children, readQuestion);
    if (source.value === "choose") body.bank_question_ids = data.getAll("bank_ids").map(Number);
    if (source.value === "random") {
      body.random_selection = {
        count: Number(data.get("count")),
        subject: data.get("bank_subject"),
        difficulty: data.get("bank_difficulty"),
      };
    }
    const { exam } = await apiFetch("/api/exams", { method: "POST", body });
    modal.close();
    await refresh();
    await showExamPaper(exam.id);
  });
}

export { editExamSchedule } from "./exam-schedule.js";
