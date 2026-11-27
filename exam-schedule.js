import { apiFetch } from "./api.js";
import { dialog, bindSubmit } from "./assessment-dialog.js";

export function localInput(value) {
  if (!value) return "";
  const date = new Date(value);
  const timestamp = date.getTime() - date.getTimezoneOffset() * 60_000;
  return new Date(timestamp).toISOString().slice(0, 16);
}

export function scheduleFields(exam = {}) {
  return `<div class="grid grid-2">
    <label>Opens for new attempts<input type="datetime-local" name="opens_at" value="${localInput(exam.opens_at)}"></label>
    <label>Closes for new attempts<input type="datetime-local" name="closes_at" value="${localInput(exam.closes_at)}"></label>
  </div>`;
}

export function readSchedule(data) {
  return Object.fromEntries(["opens_at", "closes_at"].map((key) => [
    key, data.get(key) ? new Date(data.get(key)).toISOString() : null,
  ]));
}

export function editExamSchedule(exam, refresh) {
  const modal = dialog("Edit start window", `
    <form class="assessment-controls">${scheduleFields(exam)}
      <button type="submit" class="btn btn-primary">Save schedule</button>
    </form>`);
  const form = modal.querySelector("form");
  bindSubmit(form, async () => {
    await apiFetch(`/api/exams/${exam.id}/schedule`, {
      method: "PATCH", body: readSchedule(new FormData(form)),
    });
    modal.close();
    await refresh();
  });
}
