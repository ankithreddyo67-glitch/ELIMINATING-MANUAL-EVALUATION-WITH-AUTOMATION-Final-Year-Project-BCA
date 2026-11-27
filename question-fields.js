import { escapeHtml } from "./api.js";

export const types = {
  MCQ: "Multiple choice",
  TRUE_FALSE: "True / False",
  SHORT: "Short answer",
  SUBJECTIVE: "Descriptive",
  PROGRAMMING: "Programming",
};
export const difficulties = { EASY: "Easy", MEDIUM: "Medium", HARD: "Hard" };

export function choices(items, selected) {
  return Object.entries(items).map(([value, label]) =>
    `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`
  ).join("");
}

export function questionFields(question = {}) {
  const fields = document.createElement("fieldset");
  fields.className = "question-fields";
  fields.innerHTML = `
    <div class="grid grid-3">
      <label>Type<select name="question_type">${choices(types, question.question_type || "MCQ")}</select></label>
      <label>Difficulty<select name="difficulty">${choices(difficulties, question.difficulty || "MEDIUM")}</select></label>
      <label>Maximum marks<input type="number" min="0.5" step="any" name="max_marks" value="${question.max_marks ?? 5}" required></label>
    </div>
    <label>Subject<input name="subject" value="${escapeHtml(question.subject)}" placeholder="${question.inline ? "Uses the exam subject" : "e.g. Python"}" ${question.inline ? "" : "required"}></label>
    <label>Question<textarea name="prompt" rows="2" required>${escapeHtml(question.prompt)}</textarea></label>
    <div data-mcq class="grid grid-2">
      ${[..."ABCD"].map((letter, i) => `
        <label>Option ${letter}<input name="option-${letter}" value="${escapeHtml(question.options?.[i]?.replace(/^[A-D][.)]\s*/, ""))}" ${i < 2 ? "required" : ""}></label>`).join("")}
      <label>Correct option<select name="mcq_answer">${choices({ A: "A", B: "B", C: "C", D: "D" }, question.model_answer)}</select></label>
    </div>
    <label data-tf>Correct answer<select name="tf_answer">${choices({ True: "True", False: "False" }, question.model_answer)}</select></label>
    <label data-text>Reference answer<textarea name="reference" rows="4" required>${escapeHtml(question.model_answer)}</textarea></label>
    <label data-rubric>Rubric keywords (comma-separated)<input name="keywords" value="${escapeHtml(question.keywords?.join(", "))}"></label>`;

  const kind = fields.querySelector('[name="question_type"]');
  const sync = () => {
    const groups = {
      mcq: kind.value === "MCQ",
      tf: kind.value === "TRUE_FALSE",
      text: !["MCQ", "TRUE_FALSE"].includes(kind.value),
      rubric: ["SHORT", "SUBJECTIVE"].includes(kind.value),
    };
    for (const [name, visible] of Object.entries(groups)) {
      const group = fields.querySelector(`[data-${name}]`);
      group.hidden = !visible;
      group.querySelectorAll("input, select, textarea").forEach((input) => { input.disabled = !visible; });
    }
    fields.querySelector('[name="reference"]').classList.toggle("code-answer", kind.value === "PROGRAMMING");
  };
  kind.onchange = sync;
  sync();
  return fields;
}

export function readQuestion(fields) {
  const value = (name) => fields.querySelector(`[name="${name}"]`).value;
  const question_type = value("question_type");
  const answerField = { MCQ: "mcq_answer", TRUE_FALSE: "tf_answer" }[question_type] || "reference";
  const options = question_type === "MCQ" ? [..."ABCD"].map((letter) => value(`option-${letter}`).trim()) : [];
  while (options.length > 2 && !options.at(-1)) options.pop();
  return {
    question_type,
    options,
    subject: value("subject").trim(),
    difficulty: value("difficulty"),
    max_marks: Number(value("max_marks")),
    prompt: value("prompt").trim(),
    model_answer: value(answerField),
    keywords: ["SHORT", "SUBJECTIVE"].includes(question_type) ? value("keywords") : "",
  };
}
