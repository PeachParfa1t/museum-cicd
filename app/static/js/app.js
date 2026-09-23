const resources = {
  exhibits: {
    title: "Экспонаты",
    description: "Учёт музейных предметов и мест их хранения",
    singular: "экспонат",
    columns: [
      { key: "inventory_number", label: "Инвентарный №", tag: true },
      { key: "title", label: "Название", subtitle: "material" },
      { key: "creation_year", label: "Год" },
      { key: "collection_name", label: "Коллекция" },
      { key: "hall_name", label: "Зал" },
    ],
    fields: [
      { name: "inventory_number", label: "Инвентарный номер", required: true },
      { name: "title", label: "Название", required: true },
      { name: "creation_year", label: "Год создания", type: "number" },
      { name: "material", label: "Материал", required: true },
      { name: "collection_id", label: "Коллекция", type: "select", source: "collections" },
      { name: "hall_id", label: "Зал", type: "select", source: "halls" },
    ],
  },
  collections: {
    title: "Коллекции",
    description: "Тематические фонды и направления комплектования",
    singular: "коллекцию",
    columns: [
      { key: "name", label: "Название", subtitle: "description" },
      { key: "theme", label: "Тематика" },
      { key: "founded_year", label: "Год основания" },
    ],
    fields: [
      { name: "name", label: "Название", required: true },
      { name: "theme", label: "Тематика", required: true },
      { name: "founded_year", label: "Год основания", type: "number" },
      { name: "description", label: "Описание", type: "textarea", full: true },
    ],
  },
  halls: {
    title: "Залы",
    description: "Экспозиционные пространства музея",
    singular: "зал",
    columns: [
      { key: "name", label: "Название", subtitle: "description" },
      { key: "floor", label: "Этаж" },
      { key: "capacity", label: "Вместимость" },
    ],
    fields: [
      { name: "name", label: "Название", required: true },
      { name: "floor", label: "Этаж", type: "number", required: true },
      { name: "capacity", label: "Вместимость", type: "number", required: true },
      { name: "description", label: "Описание", type: "textarea", full: true },
    ],
  },
  employees: {
    title: "Сотрудники",
    description: "Команда музея и контактные данные",
    singular: "сотрудника",
    columns: [
      { key: "full_name", label: "Сотрудник", subtitle: "email" },
      { key: "position", label: "Должность" },
      { key: "phone", label: "Телефон" },
    ],
    fields: [
      { name: "full_name", label: "ФИО", required: true },
      { name: "position", label: "Должность", required: true },
      { name: "email", label: "Электронная почта", type: "email", required: true },
      { name: "phone", label: "Телефон", type: "tel" },
    ],
  },
  events: {
    title: "События",
    description: "Выставки, встречи и образовательные программы",
    singular: "событие",
    columns: [
      { key: "title", label: "Название", subtitle: "description" },
      { key: "event_date", label: "Дата", format: "date" },
      { key: "location", label: "Место" },
    ],
    fields: [
      { name: "title", label: "Название", required: true },
      { name: "event_date", label: "Дата", type: "date", required: true },
      { name: "location", label: "Место", required: true },
      { name: "description", label: "Описание", type: "textarea", full: true },
    ],
  },
};

const state = {
  resource: "exhibits",
  records: [],
  editingId: null,
};

const elements = {
  title: document.querySelector("#page-title"),
  description: document.querySelector("#page-description"),
  head: document.querySelector("#table-head"),
  body: document.querySelector("#table-body"),
  tableWrap: document.querySelector(".table-wrap"),
  empty: document.querySelector("#empty-state"),
  count: document.querySelector("#record-count"),
  search: document.querySelector("#search-input"),
  addButton: document.querySelector("#add-button"),
  addLabel: document.querySelector("#add-button-label"),
  dialog: document.querySelector("#record-dialog"),
  form: document.querySelector("#record-form"),
  fields: document.querySelector("#form-fields"),
  dialogTitle: document.querySelector("#dialog-title"),
  toast: document.querySelector("#toast"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Ошибка сервера: ${response.status}`);
  }

  return response.status === 204 ? null : response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatValue(value, column) {
  if (value === null || value === undefined || value === "") return "—";
  if (column.format === "date") {
    return new Intl.DateTimeFormat("ru-RU").format(new Date(`${value}T00:00:00`));
  }
  return value;
}

function showToast(message, error = false) {
  elements.toast.textContent = message;
  elements.toast.classList.toggle("error", error);
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => {
    elements.toast.classList.remove("visible");
  }, 2800);
}

async function loadStats() {
  const stats = await api("/api/stats");
  for (const [key, value] of Object.entries(stats)) {
    const target = document.querySelector(`#stat-${key}`);
    if (target) target.textContent = value;
  }
}

async function loadRecords() {
  try {
    state.records = await api(`/api/${state.resource}`);
    renderTable();
  } catch (error) {
    showToast(error.message, true);
  }
}

function visibleRecords() {
  const query = elements.search.value.trim().toLocaleLowerCase("ru");
  if (!query) return state.records;
  return state.records.filter((record) =>
    Object.values(record).some((value) =>
      String(value ?? "").toLocaleLowerCase("ru").includes(query)
    )
  );
}

function renderTable() {
  const config = resources[state.resource];
  const records = visibleRecords();

  elements.head.innerHTML = `<tr>${config.columns
    .map((column) => `<th>${escapeHtml(column.label)}</th>`)
    .join("")}<th><span class="visually-hidden">Действия</span></th></tr>`;

  elements.body.innerHTML = records
    .map(
      (record) => `<tr>${config.columns
        .map((column) => {
          const value = escapeHtml(formatValue(record[column.key], column));
          if (column.tag) return `<td><span class="tag">${value}</span></td>`;
          if (column.subtitle) {
            const subtitle = escapeHtml(record[column.subtitle] || "");
            return `<td><span class="record-title">${value}</span><span class="record-subtitle">${subtitle}</span></td>`;
          }
          return `<td>${value}</td>`;
        })
        .join("")}
        <td class="actions-cell">
          <button class="table-action edit" data-id="${record.id}" aria-label="Изменить">✎</button>
          <button class="table-action delete" data-id="${record.id}" aria-label="Удалить">×</button>
        </td>
      </tr>`
    )
    .join("");

  const isEmpty = records.length === 0;
  elements.tableWrap.hidden = isEmpty;
  elements.empty.hidden = !isEmpty;
  elements.count.textContent = `Показано записей: ${records.length} из ${state.records.length}`;
}

async function switchResource(resource) {
  state.resource = resource;
  elements.search.value = "";
  const config = resources[resource];
  elements.title.textContent = config.title;
  elements.description.textContent = config.description;
  elements.addLabel.textContent = `Добавить ${config.singular}`;
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.resource === resource);
  });
  await loadRecords();
}

async function buildForm(record = {}) {
  const config = resources[state.resource];
  const optionCache = {};
  const selectSources = [...new Set(config.fields.filter((field) => field.source).map((field) => field.source))];
  await Promise.all(
    selectSources.map(async (source) => {
      optionCache[source] = await api(`/api/${source}`);
    })
  );

  elements.fields.innerHTML = config.fields
    .map((field) => {
      const value = record[field.name] ?? "";
      const required = field.required ? "required" : "";
      const classes = field.full ? "field full" : "field";

      if (field.type === "textarea") {
        return `<div class="${classes}"><label for="field-${field.name}">${escapeHtml(field.label)}</label><textarea id="field-${field.name}" name="${field.name}" ${required}>${escapeHtml(value)}</textarea></div>`;
      }

      if (field.type === "select") {
        const options = optionCache[field.source]
          .map((item) => `<option value="${item.id}" ${Number(value) === item.id ? "selected" : ""}>${escapeHtml(item.name)}</option>`)
          .join("");
        return `<div class="${classes}"><label for="field-${field.name}">${escapeHtml(field.label)}</label><select id="field-${field.name}" name="${field.name}"><option value="">Не выбрано</option>${options}</select></div>`;
      }

      return `<div class="${classes}"><label for="field-${field.name}">${escapeHtml(field.label)}</label><input id="field-${field.name}" name="${field.name}" type="${field.type || "text"}" value="${escapeHtml(value)}" ${required}></div>`;
    })
    .join("");
}

async function openCreateDialog() {
  state.editingId = null;
  elements.dialogTitle.textContent = `Новый ${resources[state.resource].singular}`;
  await buildForm();
  elements.dialog.showModal();
}

async function openEditDialog(id) {
  try {
    state.editingId = id;
    const record = await api(`/api/${state.resource}/${id}`);
    elements.dialogTitle.textContent = "Изменение записи";
    await buildForm(record);
    elements.dialog.showModal();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function saveRecord(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(elements.form).entries());
  const path = state.editingId
    ? `/api/${state.resource}/${state.editingId}`
    : `/api/${state.resource}`;

  try {
    await api(path, {
      method: state.editingId ? "PUT" : "POST",
      body: JSON.stringify(data),
    });
    elements.dialog.close();
    showToast(state.editingId ? "Запись изменена" : "Запись добавлена");
    await Promise.all([loadRecords(), loadStats()]);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function deleteRecord(id) {
  if (!window.confirm("Удалить эту запись? Действие нельзя отменить.")) return;
  try {
    await api(`/api/${state.resource}/${id}`, { method: "DELETE" });
    showToast("Запись удалена");
    await Promise.all([loadRecords(), loadStats()]);
  } catch (error) {
    showToast(error.message, true);
  }
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => switchResource(button.dataset.resource));
});

elements.addButton.addEventListener("click", openCreateDialog);
elements.search.addEventListener("input", renderTable);
elements.form.addEventListener("submit", saveRecord);
document.querySelector("#close-dialog").addEventListener("click", () => elements.dialog.close());
document.querySelector("#cancel-button").addEventListener("click", () => elements.dialog.close());

elements.body.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-id]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.classList.contains("edit")) openEditDialog(id);
  if (button.classList.contains("delete")) deleteRecord(id);
});

Promise.all([loadStats(), loadRecords()]).catch((error) => showToast(error.message, true));
