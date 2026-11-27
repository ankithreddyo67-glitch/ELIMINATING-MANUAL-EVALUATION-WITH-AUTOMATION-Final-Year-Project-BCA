import { escapeHtml } from "./api.js";

export function dialog(title, contents) {
  const modal = document.createElement("dialog");
  modal.className = "assessment-dialog";
  modal.innerHTML = `
    <div class="card-header"><h2 class="card-title">${escapeHtml(title)}</h2>
      <button type="button" class="btn btn-sm" data-close>Close</button>
    </div>
    ${contents}`;
  modal.querySelector("[data-close]").onclick = () => modal.close();
  modal.addEventListener("close", () => modal.remove(), { once: true });
  document.body.append(modal);
  modal.showModal();
  return modal;
}

export function bindSubmit(form, submit) {
  const errorMessage = document.createElement("p");
  errorMessage.className = "badge badge-danger";
  errorMessage.setAttribute("role", "alert");
  errorMessage.hidden = true;
  form.append(errorMessage);
  form.onsubmit = async (event) => {
    errorMessage.hidden = true;
    event.preventDefault();
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      await submit();
    } catch (error) {
      errorMessage.textContent = error.message;
      errorMessage.hidden = false;
    } finally {
      button.disabled = false;
    }
  };
}
