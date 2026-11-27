import { escapeHtml } from "./api.js";

export function openAdminForm(title, fields, save) {
  const dialog = document.createElement("dialog");
  dialog.className = "assessment-dialog";
  dialog.innerHTML = `<div class="card-header"><h2>${escapeHtml(title)}</h2>
    <button type="button" class="btn" data-close>Close</button></div>
    <form class="assessment-controls">${fields}<p role="alert" hidden></p>
    <button type="submit" class="btn btn-primary">Save</button></form>`;
  dialog.querySelector("[data-close]").onclick = () => dialog.close();
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
  const form = dialog.querySelector("form");
  form.onsubmit = async (event) => {
    event.preventDefault();
    const saveButton = form.querySelector('[type="submit"]');
    const error = form.querySelector('[role="alert"]');
    error.hidden = true;
    saveButton.disabled = true;
    try {
      await save(new FormData(form));
      dialog.close();
    } catch (err) {
      error.textContent = err.message;
      error.hidden = false;
      saveButton.disabled = false;
    }
  };
  document.body.append(dialog);
  dialog.showModal();
}
