
const API = {
    dashboard: "/dashboard/",
    categories: "/categories/",
    items: "/items/",
    tasks: "/maintenance-tasks/",
    movements: "/stock-movements/",
};

const state = {
    page: "dashboard",
    itemPage: 1,
    taskPage: 1,
    movementPage: 1,
    pageSize: 10,
    categories: [],
    items: [],
    allItems: [],
    alertTimer: null,
};

const $ = (selector) => document.querySelector(selector);

/* -------------------------------------------------------------------------- */
/* Utilities                                                                  */
/* -------------------------------------------------------------------------- */

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    })[char]);
}

function formatDate(value) {
    if (!value) return "—";

    const raw = String(value);

    // Date-only values must not shift to the previous day.
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        const [year, month, day] = raw.split("-").map(Number);
        return new Date(year, month - 1, day).toLocaleDateString();
    }

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? escapeHTML(value)
        : date.toLocaleDateString();
}

function showAlert(message, type = "success") {
    const area = $("#alert-area");

    if (!area) return;

    if (state.alertTimer) {
        window.clearTimeout(state.alertTimer);
        state.alertTimer = null;
    }

    const safeType = ["success", "error", "warning", "info"].includes(type)
        ? type
        : "success";

    area.innerHTML = `
        <div class="alert alert-${safeType}" role="alert">
            ${escapeHTML(message)}
        </div>
    `;

    state.alertTimer = window.setTimeout(() => {
        area.innerHTML = "";
        state.alertTimer = null;
    }, 5000);
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            ...(options.body
                ? { "Content-Type": "application/json" }
                : {}),
            ...options.headers,
        },
    });

    if (!response.ok) {
        let message = `Request failed (${response.status})`;

        try {
            const data = await response.json();

            message = typeof data.detail === "string"
                ? data.detail
                : JSON.stringify(data.detail || data);
        } catch {
            // Keep the HTTP status message.
        }

        throw new Error(message);
    }

    if (response.status === 204) {
        return null;
    }

    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        return response.json();
    }

    return null;
}

function badge(value) {
    const classes = {
        IN: "badge-green",
        OUT: "badge-red",
        ADJUSTMENT: "badge-blue",

        OPEN: "badge-orange",
        IN_PROGRESS: "badge-blue",
        COMPLETED: "badge-green",
        CANCELLED: "badge-gray",

        HIGH: "badge-red",
        MEDIUM: "badge-orange",
        LOW: "badge-gray",
    };

    const label = String(value || "UNKNOWN").replaceAll("_", " ");

    return `
        <span class="badge ${classes[value] || "badge-gray"}">
            ${escapeHTML(label)}
        </span>
    `;
}

function emptyRow(columns, message) {
    return `
        <tr>
            <td colspan="${columns}" class="empty-state">
                ${escapeHTML(message)}
            </td>
        </tr>
    `;
}

/* -------------------------------------------------------------------------- */
/* Navigation                                                                 */
/* -------------------------------------------------------------------------- */

function setPage(page) {
    const validPages = [
        "dashboard",
        "items",
        "categories",
        "movements",
        "maintenance",
    ];

    if (!validPages.includes(page)) return;

    state.page = page;

    document.querySelectorAll(".page-section").forEach((section) => {
        section.classList.toggle(
            "active",
            section.id === `page-${page}`
        );
    });

    document.querySelectorAll(".nav-link").forEach((link) => {
        link.classList.toggle(
            "active",
            link.dataset.page === page
        );
    });

    const titles = {
        dashboard: "Dashboard",
        items: "Inventory",
        categories: "Categories",
        movements: "Stock movements",
        maintenance: "Maintenance",
    };

    $("#page-title").textContent = titles[page];
    $("#breadcrumb-current").textContent = titles[page];

    $("#sidebar").classList.remove("open");
    $("#mobile-menu")?.setAttribute("aria-expanded", "false");

    const loaders = {
        dashboard: loadDashboard,
        items: loadItems,
        categories: loadCategories,
        movements: loadMovements,
        maintenance: loadTasks,
    };

    loaders[page]();
}

function renderPagination(container, page, totalPages, callback) {
    if (!container) return;

    const total = Math.max(1, Number(totalPages) || 1);
    const current = Math.max(1, Number(page) || 1);

    container.innerHTML = `
        <button
            type="button"
            ${current <= 1 ? "disabled" : ""}
            data-direction="-1"
        >
            Previous
        </button>

        <span>Page ${current} of ${total}</span>

        <button
            type="button"
            ${current >= total ? "disabled" : ""}
            data-direction="1"
        >
            Next
        </button>
    `;

    container.querySelectorAll("button").forEach((button) => {
        button.addEventListener("click", () => {
            callback(current + Number(button.dataset.direction));
        });
    });
}

/* -------------------------------------------------------------------------- */
/* Categories                                                                 */
/* -------------------------------------------------------------------------- */

async function loadCategories() {
    try {
        const data = await apiRequest(API.categories);

        state.categories = Array.isArray(data) ? data : [];

        const categoryFilter = $("#item-category");

        if (categoryFilter) {
            const selected = categoryFilter.value;

            categoryFilter.innerHTML =
                '<option value="">All categories</option>' +
                state.categories.map((category) => `
                    <option value="${category.id}">
                        ${escapeHTML(category.name)}
                    </option>
                `).join("");

            categoryFilter.value = selected;
        }

        const grid = $("#categories-grid");

        if (!grid) return;

        grid.innerHTML = state.categories.length
            ? state.categories.map((category) => `
                <article class="category-card">
                    <div class="card-actions">
                        <button
                            type="button"
                            class="text-button"
                            data-edit-category="${category.id}"
                        >
                            Edit
                        </button>

                        <button
                            type="button"
                            class="text-button danger-text"
                            data-delete-category="${category.id}"
                        >
                            Delete
                        </button>
                    </div>

                    <h3>${escapeHTML(category.name)}</h3>

                    <p>
                        ${escapeHTML(
                            category.description || "No description provided."
                        )}
                    </p>

                    <div class="category-count">
                        ${category.item_count ?? "—"}
                        <small>Equipment items</small>
                    </div>
                </article>
            `).join("")
            : '<p class="empty-state">No categories created yet.</p>';

        grid.querySelectorAll("[data-edit-category]").forEach((button) => {
            button.addEventListener("click", () => {
                editCategory(Number(button.dataset.editCategory));
            });
        });

        grid.querySelectorAll("[data-delete-category]").forEach((button) => {
            button.addEventListener("click", () => {
                deleteCategory(Number(button.dataset.deleteCategory));
            });
        });

    } catch (error) {
        showAlert(`Categories: ${error.message}`, "error");
    }
}

function categoryOptions() {
    return state.categories.map((category) => [
        category.id,
        category.name,
    ]);
}

/* -------------------------------------------------------------------------- */
/* Load every equipment page                                                  */
/* -------------------------------------------------------------------------- */

async function loadAllItems() {
    const firstPage = await apiRequest(
        `${API.items}?page=1&page_size=100&sort_by=name&order=asc`
    );

    let allItems = firstPage.items || [];

    const totalPages = Number(firstPage.total_pages) || 1;

    for (let page = 2; page <= totalPages; page++) {
        const data = await apiRequest(
            `${API.items}?page=${page}&page_size=100&sort_by=name&order=asc`
        );

        allItems = allItems.concat(data.items || []);
    }

    state.allItems = allItems;

    return state.allItems;
}

/* -------------------------------------------------------------------------- */
/* Dashboard                                                                  */
/* -------------------------------------------------------------------------- */

async function loadDashboard() {
    const formatNumber = (value) =>
        new Intl.NumberFormat().format(Number(value) || 0);

    const toCount = (value) => {
        const number = Number(value);
        return Number.isFinite(number) ? Math.max(0, Math.floor(number)) : 0;
    };

    try {
        const data = await apiRequest(API.dashboard);

        const inventory = data.inventory || {};

        /* --------------------------------------------------
           1. Main inventory statistics
        -------------------------------------------------- */

        const totalItems = toCount(inventory.total_items);
        const totalUnits = toCount(inventory.total_stock_units);
        const lowStock = toCount(inventory.low_stock_items);
        const outOfStock = toCount(inventory.out_of_stock_items);

        $("#stat-items").textContent = formatNumber(totalItems);
        $("#stat-units").textContent = formatNumber(totalUnits);
        $("#stat-low").textContent = formatNumber(lowStock);
        $("#stat-empty").textContent = formatNumber(outOfStock);

        /* --------------------------------------------------
           2. Inventory health donut chart
        -------------------------------------------------- */

        const healthyStock = Math.max(
            0,
            totalItems - lowStock - outOfStock
        );

        const classifiedItems = healthyStock + lowStock + outOfStock;
        const circumference = 2 * Math.PI * 68;

        const healthSegments = [
            {
                id: "health-ring-healthy",
                count: healthyStock,
                color: "healthy",
            },
            {
                id: "health-ring-low",
                count: lowStock,
                color: "low",
            },
            {
                id: "health-ring-empty",
                count: outOfStock,
                color: "empty",
            },
        ];

        let accumulatedLength = 0;

        healthSegments.forEach((segment) => {
            const element = document.getElementById(segment.id);

            if (!element) return;

            const ratio = classifiedItems
                ? segment.count / classifiedItems
                : 0;

            const length = circumference * ratio;

            element.style.strokeDasharray =
                `${length} ${circumference - length}`;

            element.style.strokeDashoffset = `${-accumulatedLength}`;

            accumulatedLength += length;
        });

        const healthyPercentage = classifiedItems
            ? Math.round((healthyStock / classifiedItems) * 100)
            : 0;

        const percentageElement = $("#inventory-health-percent");
        const captionElement = document.querySelector(".health-chart-caption");

        if (percentageElement) {
            percentageElement.textContent =
                classifiedItems ? `${healthyPercentage}%` : "0%";
        }

        if (captionElement) {
            captionElement.textContent =
                totalItems > 0 ? "HEALTHY" : "NO ITEMS";
        }

        const healthLegend = [
            ["#health-healthy", healthyStock],
            ["#health-low", lowStock],
            ["#health-empty", outOfStock],
        ];

        healthLegend.forEach(([selector, count]) => {
            const element = document.querySelector(selector);

            if (!element) return;

            const percentage = classifiedItems
                ? Math.round((count / classifiedItems) * 100)
                : 0;

            element.textContent =
                `${formatNumber(count)} (${percentage}%)`;
        });

        const chart = $("#inventory-health-chart");

        if (chart) {
            chart.setAttribute(
                "aria-label",
                `Inventory health: ${healthyStock} healthy, ` +
                `${lowStock} low stock, ${outOfStock} out of stock`
            );
        }

        /* --------------------------------------------------
           3. Inventory by category
        -------------------------------------------------- */

        const categories = data.categories || [];

        const categorySummary = $("#category-summary");

        const totalCategoryUnits = categories.reduce(
            (sum, category) => sum + toCount(category.stock_units),
            0
        );

        categorySummary.innerHTML = categories.length
            ? categories.map((category) => {
                const units = toCount(category.stock_units);

                const percentage = totalCategoryUnits
                    ? (units / totalCategoryUnits) * 100
                    : 0;

                const displayPercentage = percentage.toFixed(1);

                return `
                    <div class="category-summary-item">
                        <div class="category-line-head">
                            <span>${escapeHTML(category.name)}</span>
                            <strong>
                                ${formatNumber(units)} units
                                <span class="category-percentage">
                                    ${displayPercentage}%
                                </span>
                            </strong>
                        </div>

                        <div
                            class="progress-track"
                            role="progressbar"
                            aria-label="${escapeHTML(category.name)} stock share"
                            aria-valuemin="0"
                            aria-valuemax="100"
                            aria-valuenow="${percentage.toFixed(1)}"
                        >
                            <div
                                class="progress-fill"
                                style="width: ${percentage.toFixed(2)}%"
                            ></div>
                        </div>
                    </div>
                `;
            }).join("")
            : '<p class="empty-state">No categories yet.</p>';

        /* --------------------------------------------------
           4. Maintenance status
        -------------------------------------------------- */

        const counts = data.maintenance?.by_status || {};

        const maintenanceStatuses = [
            {
                key: "OPEN",
                label: "Open",
                className: "open",
            },
            {
                key: "IN_PROGRESS",
                label: "In progress",
                className: "progress",
            },
            {
                key: "COMPLETED",
                label: "Completed",
                className: "completed",
            },
            {
                key: "CANCELLED",
                label: "Cancelled",
                className: "cancelled",
            },
        ];

        const maintenanceCounts = maintenanceStatuses.map((status) => ({
            ...status,
            count: toCount(counts[status.key]),
        }));

        const totalTasks = maintenanceCounts.reduce(
            (sum, status) => sum + status.count,
            0
        );

        $("#maintenance-summary").innerHTML = maintenanceCounts.map(
            (status) => {
                const percentage = totalTasks
                    ? (status.count / totalTasks) * 100
                    : 0;

                return `
                    <div class="maintenance-stat maintenance-stat-${status.className}">
                        <div class="maintenance-stat-head">
                            <span>${status.label}</span>
                            <strong>${formatNumber(status.count)}</strong>
                        </div>

                        <div
                            class="maintenance-progress-track"
                            role="progressbar"
                            aria-label="${status.label} maintenance tasks"
                            aria-valuemin="0"
                            aria-valuemax="100"
                            aria-valuenow="${percentage.toFixed(1)}"
                        >
                            <div
                                class="maintenance-progress-fill"
                                style="width: ${percentage.toFixed(2)}%"
                            ></div>
                        </div>
                    </div>
                `;
            }
        ).join("");

        /* --------------------------------------------------
           5. Recent stock movements
        -------------------------------------------------- */

        const movements = data.recent_stock_movements || [];

        $("#recent-movements").innerHTML = movements.length
            ? movements.map((movement) => `
                <tr>
                    <td class="table-primary">
                        ${escapeHTML(
                            movement.item_name || `Item #${movement.item_id}`
                        )}
                    </td>

                    <td>${badge(movement.movement_type)}</td>

                    <td>
                        ${formatNumber(movement.previous_quantity)}
                        &rarr;
                        ${formatNumber(movement.new_quantity)}
                    </td>

                    <td>${formatDate(movement.created_at)}</td>
                </tr>
            `).join("")
            : emptyRow(4, "No stock movements yet.");

        /* --------------------------------------------------
           6. Recent maintenance tasks
        -------------------------------------------------- */

        const tasks = data.recent_maintenance_tasks || [];

        $("#recent-maintenance").innerHTML = tasks.length
            ? tasks.map((task) => `
                <div class="recent-item">
                    <div>
                        <strong>${escapeHTML(task.title)}</strong>

                        <small>
                            ${escapeHTML(
                                task.item_name || `Item #${task.item_id}`
                            )}
                            &middot;
                            ${formatDate(task.scheduled_date)}
                        </small>
                    </div>

                    ${badge(task.status)}
                </div>
            `).join("")
            : '<p class="empty-state">No maintenance tasks yet.</p>';

    } catch (error) {
        console.error("Dashboard loading failed:", error);

        showAlert(`Dashboard: ${error.message}`, "error");

        $("#category-summary").innerHTML =
            '<p class="empty-state">Unable to load category data.</p>';

        $("#maintenance-summary").innerHTML =
            '<p class="empty-state">Unable to load maintenance data.</p>';

        $("#recent-movements").innerHTML =
            emptyRow(4, "Unable to load stock movements.");

        $("#recent-maintenance").innerHTML =
            '<p class="empty-state">Unable to load maintenance activity.</p>';

        $("#inventory-health-percent").textContent = "—";

        [
            "#health-ring-healthy",
            "#health-ring-low",
            "#health-ring-empty",
        ].forEach((selector) => {
            const element = document.querySelector(selector);

            if (element) {
                element.style.strokeDasharray = "0 427.26";
                element.style.strokeDashoffset = "0";
            }
        });

        [
            "#stat-items",
            "#stat-units",
            "#stat-low",
            "#stat-empty",
            "#health-healthy",
            "#health-low",
            "#health-empty",
        ].forEach((selector) => {
            const element = document.querySelector(selector);

            if (element) element.textContent = "—";
        });
    }
}


/* -------------------------------------------------------------------------- */
/* Inventory                                                                  */
/* -------------------------------------------------------------------------- */

async function loadItems() {
    try {
        if (!state.categories.length) {
            await loadCategories();
        }

        const params = new URLSearchParams({
            page: state.itemPage,
            page_size: state.pageSize,
            sort_by: "name",
            order: "asc",
        });

        const search = $("#item-search").value.trim();
        const category = $("#item-category").value;
        const stock = $("#item-stock").value;

        if (search) {
            params.set("search", search);
        }

        if (category) {
            params.set("category_id", category);
        }

        if (stock === "low") {
            params.set("low_stock", "true");
        }

        if (stock === "empty") {
            params.set("out_of_stock", "true");
        }

        const data = await apiRequest(
            `${API.items}?${params.toString()}`
        );

        state.items = data.items || [];

        $("#items-table").innerHTML = state.items.length
            ? state.items.map((item) => {
                const categoryName =
                    state.categories.find(
                        (category) => category.id === item.category_id
                    )?.name || `#${item.category_id}`;

                const stockClass = item.quantity === 0
                    ? "badge-red"
                    : item.quantity <= item.minimum_stock
                        ? "badge-orange"
                        : "badge-green";

                const stockLabel = item.quantity === 0
                    ? "Out of stock"
                    : item.quantity <= item.minimum_stock
                        ? "Low stock"
                        : "In stock";

                return `
                    <tr>
                        <td class="table-primary">
                            ${escapeHTML(item.name)}
                        </td>

                        <td>${escapeHTML(item.sku)}</td>

                        <td>${escapeHTML(categoryName)}</td>

                        <td><strong>${item.quantity}</strong></td>

                        <td>${item.minimum_stock}</td>

                        <td>${escapeHTML(item.location || "—")}</td>

                        <td>
                            <span class="badge ${stockClass}">
                                ${stockLabel}
                            </span>
                        </td>

                        <td class="row-actions">
                            <button
                                type="button"
                                class="text-button"
                                data-edit-item="${item.id}"
                            >
                                Edit
                            </button>

                            <button
                                type="button"
                                class="text-button danger-text"
                                data-delete-item="${item.id}"
                            >
                                Delete
                            </button>
                        </td>
                    </tr>
                `;
            }).join("")
            : emptyRow(8, "No matching equipment found.");

        $("#items-table").querySelectorAll("[data-edit-item]").forEach((button) => {
            button.addEventListener("click", () => {
                editItem(Number(button.dataset.editItem));
            });
        });

        $("#items-table").querySelectorAll("[data-delete-item]").forEach((button) => {
            button.addEventListener("click", () => {
                deleteItem(Number(button.dataset.deleteItem));
            });
        });

        renderPagination(
            $("#items-pagination"),
            data.page,
            data.total_pages,
            (page) => {
                state.itemPage = page;
                loadItems();
            }
        );

    } catch (error) {
        showAlert(`Inventory: ${error.message}`, "error");
    }
}

/* -------------------------------------------------------------------------- */
/* Maintenance                                                                */
/* -------------------------------------------------------------------------- */

async function loadTasks() {
    try {
        if (!state.allItems.length) {
            await loadAllItems();
        }

        const params = new URLSearchParams({
            page: state.taskPage,
            page_size: state.pageSize,
            sort_by: "created_at",
            order: "desc",
        });

        const search = $("#task-search").value.trim();
        const taskStatus = $("#task-status").value;
        const priority = $("#task-priority").value;

        if (search) {
            params.set("search", search);
        }

        if (taskStatus) {
            params.set("status", taskStatus);
        }

        if (priority) {
            params.set("priority", priority);
        }

        const data = await apiRequest(
            `${API.tasks}?${params.toString()}`
        );

        const tasks = data.items || [];

        $("#tasks-table").innerHTML = tasks.length
            ? tasks.map((task) => {
                const itemName =
                    state.allItems.find(
                        (item) => item.id === task.item_id
                    )?.name || `Item #${task.item_id}`;

                return `
                    <tr>
                        <td class="table-primary">
                            ${escapeHTML(task.title)}
                        </td>

                        <td>${escapeHTML(itemName)}</td>

                        <td>${badge(task.priority)}</td>

                        <td>${badge(task.status)}</td>

                        <td>${formatDate(task.scheduled_date)}</td>

                        <td>${formatDate(task.completed_at)}</td>

                        <td class="row-actions">
                            <button
                                type="button"
                                class="text-button"
                                data-edit-task="${task.id}"
                            >
                                Edit
                            </button>

                            <button
                                type="button"
                                class="text-button danger-text"
                                data-delete-task="${task.id}"
                            >
                                Delete
                            </button>
                        </td>
                    </tr>
                `;
            }).join("")
            : emptyRow(7, "No matching maintenance tasks.");

        $("#tasks-table").querySelectorAll("[data-edit-task]").forEach((button) => {
            button.addEventListener("click", () => {
                editTask(Number(button.dataset.editTask));
            });
        });

        $("#tasks-table").querySelectorAll("[data-delete-task]").forEach((button) => {
            button.addEventListener("click", () => {
                deleteTask(Number(button.dataset.deleteTask));
            });
        });

        renderPagination(
            $("#tasks-pagination"),
            data.page,
            data.total_pages,
            (page) => {
                state.taskPage = page;
                loadTasks();
            }
        );

    } catch (error) {
        showAlert(`Maintenance: ${error.message}`, "error");
    }
}

/* -------------------------------------------------------------------------- */
/* Stock movements                                                            */
/* -------------------------------------------------------------------------- */

async function loadMovements() {
    try {
        const params = new URLSearchParams({
            page: state.movementPage,
            page_size: state.pageSize,
            sort_by: "created_at",
            order: "desc",
        });

        const search = $("#movement-search").value.trim();
        const movementType = $("#movement-type").value;

        if (search) {
            params.set("search", search);
        }

        if (movementType) {
            params.set("movement_type", movementType);
        }

        const data = await apiRequest(
            `${API.movements}?${params.toString()}`
        );

        const movements = data.items || [];

        $("#movements-table").innerHTML = movements.length
            ? movements.map((movement) => `
                <tr>
                    <td class="table-primary">
                        ${escapeHTML(
                            movement.item_name || `Item #${movement.item_id}`
                        )}
                    </td>

                    <td>${badge(movement.movement_type)}</td>

                    <td>${movement.quantity}</td>

                    <td>${movement.previous_quantity}</td>

                    <td><strong>${movement.new_quantity}</strong></td>

                    <td>${escapeHTML(movement.notes || "—")}</td>

                    <td>${formatDate(movement.created_at)}</td>
                </tr>
            `).join("")
            : emptyRow(7, "No stock movements found.");

        renderPagination(
            $("#movements-pagination"),
            data.page,
            data.total_pages,
            (page) => {
                state.movementPage = page;
                loadMovements();
            }
        );

    } catch (error) {
        showAlert(`Stock movements: ${error.message}`, "error");
    }
}

/* -------------------------------------------------------------------------- */
/* Modal form fields                                                          */
/* -------------------------------------------------------------------------- */

function field(label, name, type = "text", options = {}) {
    const required = options.required ? "required" : "";
    const full = options.full ? " full" : "";
    const id = `field-${name}`;

    let control;

    if (type === "select") {
        control = `
            <select
                id="${id}"
                name="${escapeHTML(name)}"
                ${required}
            >
                ${(options.options || []).map(([value, text]) => `
                    <option
                        value="${escapeHTML(value)}"
                        ${
                            String(value) === String(options.value ?? "")
                                ? "selected"
                                : ""
                        }
                    >
                        ${escapeHTML(text)}
                    </option>
                `).join("")}
            </select>
        `;
    } else if (type === "textarea") {
        control = `
            <textarea
                id="${id}"
                name="${escapeHTML(name)}"
                ${required}
                placeholder="${escapeHTML(options.placeholder || "")}"
            >${escapeHTML(options.value || "")}</textarea>
        `;
    } else {
        control = `
            <input
                id="${id}"
                name="${escapeHTML(name)}"
                type="${escapeHTML(type)}"
                ${required}
                ${options.readonly ? "readonly" : ""}
                ${options.min !== undefined ? `min="${options.min}"` : ""}
                ${options.step !== undefined ? `step="${options.step}"` : ""}
                value="${escapeHTML(options.value ?? "")}"
                placeholder="${escapeHTML(options.placeholder || "")}"
            >
        `;
    }

    return `
        <div class="form-field${full}">
            <label for="${id}">${escapeHTML(label)}</label>
            ${control}
        </div>
    `;
}

/* -------------------------------------------------------------------------- */
/* Modal management                                                           */
/* -------------------------------------------------------------------------- */

function openModal(title, fields, submitText, onSubmit) {
    $("#modal-title").textContent = title;
    $("#modal-fields").innerHTML = fields;
    $("#modal-submit").textContent = submitText;

    $("#modal-backdrop").hidden = false;

    const form = $("#modal-form");
    const submitButton = $("#modal-submit");

    form.onsubmit = async (event) => {
        event.preventDefault();

        if (submitButton.disabled) return;

        submitButton.disabled = true;
        submitButton.textContent = "Saving…";

        try {
            await onSubmit(new FormData(form));

            closeModal();

            showAlert("Record saved successfully.");

            await refreshCurrentPage();

        } catch (error) {
            showAlert(error.message, "error");

        } finally {
            submitButton.disabled = false;
            submitButton.textContent = submitText;
        }
    };

    const firstInput = $("#modal-fields").querySelector(
        "input, select, textarea"
    );

    firstInput?.focus();
}

function closeModal() {
    $("#modal-backdrop").hidden = true;
    $("#modal-form").reset();
}

/* -------------------------------------------------------------------------- */
/* Refresh current page                                                       */
/* -------------------------------------------------------------------------- */

async function refreshCurrentPage() {
    if (state.page === "dashboard") {
        return loadDashboard();
    }

    if (state.page === "categories") {
        return loadCategories();
    }

    if (state.page === "items") {
        await loadCategories();
        return loadItems();
    }

    if (state.page === "movements") {
        return loadMovements();
    }

    if (state.page === "maintenance") {
        state.allItems = [];
        await loadAllItems();
        return loadTasks();
    }
}

/* -------------------------------------------------------------------------- */
/* Equipment create / update / delete                                         */
/* -------------------------------------------------------------------------- */

function openItemModal(item = null) {
    if (!state.categories.length) {
        showAlert(
            "Create a category before adding equipment.",
            "error"
        );

        setPage("categories");
        return;
    }

    const editing = Boolean(item);

    openModal(
        editing ? "Edit equipment" : "Add equipment",

        field("Equipment name", "name", "text", {
            required: true,
            value: item?.name,
        }) +

        field("SKU", "sku", "text", {
            required: true,
            value: item?.sku,
        }) +

        field("Category", "category_id", "select", {
            required: true,
            options: categoryOptions(),
            value: item?.category_id,
        }) +

        field(
            editing ? "Current quantity (read-only)" : "Initial quantity",
            "quantity",
            "number",
            {
                required: !editing,
                min: 0,
                step: 1,
                value: item?.quantity,
                readonly: editing,
            }
        ) +

        field("Minimum stock", "minimum_stock", "number", {
            required: true,
            min: 0,
            step: 1,
            value: item?.minimum_stock,
        }) +

        field("Storage location", "location", "text", {
            value: item?.location,
        }) +

        field("Description", "description", "textarea", {
            full: true,
            value: item?.description,
        }),

        editing ? "Save changes" : "Create equipment",

        async (form) => {
            const payload = {
                name: form.get("name"),
                sku: form.get("sku"),
                category_id: Number(form.get("category_id")),
                minimum_stock: Number(form.get("minimum_stock")),
                location: form.get("location") || null,
                description: form.get("description") || null,
            };

            // Quantity can only be changed through stock movements.
            if (!editing) {
                payload.quantity = Number(form.get("quantity"));
            }

            await apiRequest(
                editing
                    ? `${API.items}${item.id}`
                    : API.items,
                {
                    method: editing ? "PATCH" : "POST",
                    body: JSON.stringify(payload),
                }
            );
        }
    );
}

async function editItem(id) {
    try {
        const item = await apiRequest(`${API.items}${id}`);
        openItemModal(item);
    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function deleteItem(id) {
    const item = state.items.find((entry) => entry.id === id);

    const confirmed = window.confirm(
        `Delete "${item?.name || `item #${id}`}"? This cannot be undone.`
    );

    if (!confirmed) return;

    try {
        await apiRequest(`${API.items}${id}`, {
            method: "DELETE",
        });

        showAlert("Equipment deleted.");

        await refreshCurrentPage();

    } catch (error) {
        showAlert(error.message, "error");
    }
}

/* -------------------------------------------------------------------------- */
/* Category create / update / delete                                          */
/* -------------------------------------------------------------------------- */

function openCategoryModal(category = null) {
    const editing = Boolean(category);

    openModal(
        editing ? "Edit category" : "Add category",

        field("Category name", "name", "text", {
            required: true,
            value: category?.name,
        }) +

        field("Description", "description", "textarea", {
            full: true,
            value: category?.description,
        }),

        editing ? "Save changes" : "Create category",

        async (form) => {
            const payload = {
                name: form.get("name"),
                description: form.get("description") || null,
            };

            await apiRequest(
                editing
                    ? `${API.categories}${category.id}`
                    : API.categories,
                {
                    method: editing ? "PATCH" : "POST",
                    body: JSON.stringify(payload),
                }
            );
        }
    );
}

async function editCategory(id) {
    try {
        const category = await apiRequest(`${API.categories}${id}`);
        openCategoryModal(category);
    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function deleteCategory(id) {
    const category = state.categories.find(
        (entry) => entry.id === id
    );

    const confirmed = window.confirm(
        `Delete category "${category?.name || id}"?`
    );

    if (!confirmed) return;

    try {
        await apiRequest(`${API.categories}${id}`, {
            method: "DELETE",
        });

        showAlert("Category deleted.");

        await refreshCurrentPage();

    } catch (error) {
        showAlert(error.message, "error");
    }
}

/* -------------------------------------------------------------------------- */
/* Stock movement creation                                                   */
/* -------------------------------------------------------------------------- */

async function openMovementModal() {
    try {
        await loadAllItems();

        if (!state.allItems.length) {
            showAlert(
                "Add equipment before recording a stock movement.",
                "error"
            );

            setPage("items");
            return;
        }

        openModal(
            "Record stock movement",

            field("Equipment", "item_id", "select", {
                required: true,
                full: true,
                options: state.allItems.map((item) => [
                    item.id,
                    `${item.name} (${item.sku}) · ${item.quantity} units`,
                ]),
            }) +

            field("Movement type", "movement_type", "select", {
                required: true,
                options: [
                    ["IN", "Stock IN"],
                    ["OUT", "Stock OUT"],
                    ["ADJUSTMENT", "Physical count adjustment"],
                ],
            }) +

            field("Quantity", "quantity", "number", {
                required: true,
                min: 0,
                step: 1,
            }) +

            field("Notes", "notes", "textarea", {
                full: true,
            }),

            "Save movement",

            async (form) => {
                const itemId = Number(form.get("item_id"));

                const payload = {
                    movement_type: form.get("movement_type"),
                    quantity: Number(form.get("quantity")),
                    notes: form.get("notes") || null,
                };

                // The backend defines ADJUSTMENT quantity as the
                // actual counted stock, not the difference.
                await apiRequest(
                    `${API.items}${itemId}/movements/`,
                    {
                        method: "POST",
                        body: JSON.stringify(payload),
                    }
                );
            }
        );

    } catch (error) {
        showAlert(error.message, "error");
    }
}

/* -------------------------------------------------------------------------- */
/* Maintenance create / update / delete                                       */
/* -------------------------------------------------------------------------- */

async function openTaskModal(task = null) {
    try {
        await loadAllItems();

        if (!state.allItems.length) {
            showAlert(
                "Add equipment before creating a maintenance task.",
                "error"
            );

            setPage("items");
            return;
        }

        const editing = Boolean(task);

        openModal(
            editing
                ? "Edit maintenance task"
                : "Create maintenance task",

            field("Equipment", "item_id", "select", {
                required: true,
                full: true,
                options: state.allItems.map((item) => [
                    item.id,
                    item.name,
                ]),
                value: task?.item_id,
            }) +

            field("Task title", "title", "text", {
                required: true,
                full: true,
                value: task?.title,
            }) +

            field("Priority", "priority", "select", {
                required: true,
                options: [
                    ["LOW", "Low"],
                    ["MEDIUM", "Medium"],
                    ["HIGH", "High"],
                ],
                value: task?.priority || "MEDIUM",
            }) +

            field("Status", "status", "select", {
                required: true,
                options: [
                    ["OPEN", "Open"],
                    ["IN_PROGRESS", "In progress"],
                    ["COMPLETED", "Completed"],
                    ["CANCELLED", "Cancelled"],
                ],
                value: task?.status || "OPEN",
            }) +

            field("Scheduled date", "scheduled_date", "date", {
                value: task?.scheduled_date,
            }) +

            field("Description", "description", "textarea", {
                full: true,
                value: task?.description,
            }),

            editing ? "Save changes" : "Create task",

            async (form) => {
                const payload = {
                    item_id: Number(form.get("item_id")),
                    title: form.get("title"),
                    priority: form.get("priority"),
                    status: form.get("status"),
                    scheduled_date: form.get("scheduled_date") || null,
                    description: form.get("description") || null,
                };

                // Keep the equipment relationship unchanged when editing.
                if (editing) {
                    delete payload.item_id;
                }

                await apiRequest(
                    editing
                        ? `${API.tasks}${task.id}`
                        : API.tasks,
                    {
                        method: editing ? "PATCH" : "POST",
                        body: JSON.stringify(payload),
                    }
                );
            }
        );

    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function editTask(id) {
    try {
        const task = await apiRequest(`${API.tasks}${id}`);
        await openTaskModal(task);
    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function deleteTask(id) {
    const confirmed = window.confirm(
        "Delete this maintenance task?"
    );

    if (!confirmed) return;

    try {
        await apiRequest(`${API.tasks}${id}`, {
            method: "DELETE",
        });

        showAlert("Maintenance task deleted.");

        await refreshCurrentPage();

    } catch (error) {
        showAlert(error.message, "error");
    }
}

/* -------------------------------------------------------------------------- */
/* Event listeners                                                            */
/* -------------------------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", async () => {
    $("#today-label").textContent = new Date().toLocaleDateString(undefined, {
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric",
    });

    /* --------------------------------------------------
       Navigation
    -------------------------------------------------- */

    document.querySelectorAll("[data-page]").forEach((element) => {
        element.addEventListener("click", (event) => {
            if (element.tagName === "A") {
                event.preventDefault();
            }

            setPage(element.dataset.page);
        });
    });

    /* --------------------------------------------------
       Responsive sidebar
    -------------------------------------------------- */

    const appShell = document.querySelector(".app-shell");
    const sidebar = $("#sidebar");
    const sidebarToggle = $("#sidebar-toggle");
    const mobileMenu = $("#mobile-menu");
    const mobileQuery = window.matchMedia("(max-width: 760px)");

    const sidebarStorageKey = "benchtrack-sidebar-collapsed";

    function saveSidebarPreference(collapsed) {
        try {
            localStorage.setItem(
                sidebarStorageKey,
                collapsed ? "true" : "false"
            );
        } catch (error) {
            console.warn("Unable to save sidebar preference.", error);
        }
    }

    function setSidebarCollapsed(collapsed, persist = true) {
        if (!appShell) return;

        appShell.classList.toggle("sidebar-collapsed", collapsed);

        if (sidebarToggle) {
            sidebarToggle.setAttribute(
                "aria-expanded",
                String(!collapsed)
            );

            sidebarToggle.setAttribute(
                "aria-label",
                collapsed ? "Expand sidebar" : "Collapse sidebar"
            );

            sidebarToggle.title = collapsed
                ? "Expand sidebar"
                : "Collapse sidebar";
        }

        if (persist) {
            saveSidebarPreference(collapsed);
        }
    }

    function closeMobileSidebar() {
        sidebar?.classList.remove("open");
        mobileMenu?.setAttribute("aria-expanded", "false");
    }

    function restoreSidebarPreference() {
        try {
            const saved = localStorage.getItem(sidebarStorageKey);

            setSidebarCollapsed(saved === "true", false);
        } catch (error) {
            console.warn("Unable to restore sidebar preference.", error);
            setSidebarCollapsed(false, false);
        }
    }

    restoreSidebarPreference();

    document.querySelectorAll(".nav-link").forEach((link) => {
        const label = link.querySelector(".nav-text")?.textContent.trim();

        if (label) {
            link.title = label;
        }
    });

    sidebarToggle?.addEventListener("click", () => {
        if (mobileQuery.matches) return;

        const collapsed = appShell.classList.contains(
            "sidebar-collapsed"
        );

        setSidebarCollapsed(!collapsed);
    });

    mobileMenu?.addEventListener("click", () => {
        const isOpen = sidebar.classList.toggle("open");

        mobileMenu.setAttribute("aria-expanded", String(isOpen));
    });

    document.addEventListener("click", (event) => {
        if (!mobileQuery.matches || !sidebar.classList.contains("open")) {
            return;
        }

        const clickedInsideSidebar = sidebar.contains(event.target);
        const clickedMenuButton = mobileMenu?.contains(event.target);

        if (!clickedInsideSidebar && !clickedMenuButton) {
            closeMobileSidebar();
        }
    });

    const handleSidebarBreakpoint = () => {
        closeMobileSidebar();
    };

    mobileQuery.addEventListener("change", handleSidebarBreakpoint);

    /* --------------------------------------------------
       General controls
    -------------------------------------------------- */

    $("#refresh-button").addEventListener("click", refreshCurrentPage);

    // Modal controls
    $("#modal-close").addEventListener("click", closeModal);
    $("#modal-cancel").addEventListener("click", closeModal);

    $("#modal-backdrop").addEventListener("click", (event) => {
        if (event.target === $("#modal-backdrop")) {
            closeModal();
        }
    });

    // Create buttons
    $("#add-item-button").addEventListener("click", () => {
        openItemModal();
    });

    $("#add-category-button").addEventListener("click", () => {
        openCategoryModal();
    });

    $("#add-movement-button").addEventListener("click", openMovementModal);

    $("#add-task-button").addEventListener("click", () => {
        openTaskModal();
    });

    // Inventory filters
    const applyItemFilters = () => {
        state.itemPage = 1;
        loadItems();
    };

    $("#item-filter-button").addEventListener("click", applyItemFilters);

    $("#item-search").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            applyItemFilters();
        }
    });

    $("#item-category").addEventListener("change", applyItemFilters);
    $("#item-stock").addEventListener("change", applyItemFilters);

    // Maintenance filters
    const applyTaskFilters = () => {
        state.taskPage = 1;
        loadTasks();
    };

    $("#task-filter-button").addEventListener("click", applyTaskFilters);

    $("#task-search").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            applyTaskFilters();
        }
    });

    $("#task-status").addEventListener("change", applyTaskFilters);
    $("#task-priority").addEventListener("change", applyTaskFilters);

    // Stock movement filters
    const applyMovementFilters = () => {
        state.movementPage = 1;
        loadMovements();
    };

    $("#movement-filter-button").addEventListener("click", applyMovementFilters);

    $("#movement-search").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            applyMovementFilters();
        }
    });

    $("#movement-type").addEventListener("change", applyMovementFilters);

    // Escape closes the modal and mobile navigation.
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            if (!$("#modal-backdrop").hidden) {
                closeModal();
            }

            $("#sidebar").classList.remove("open");
        }
    });

    // Initial data loading
    await loadCategories();

    await loadAllItems().catch((error) => {
        console.warn("Initial equipment loading:", error);
    });

    setPage("dashboard");
});

/* =========================================================
   BENCHTRACK | THEME PREFERENCES
   ========================================================= */

(() => {
    const root = document.documentElement;
    const toggleButton = document.getElementById("theme-toggle");
    const themeLabel = document.getElementById("theme-label");

    if (!toggleButton || !themeLabel) {
        console.warn("Theme controls were not found in the page.");
        return;
    }

    const modes = ["light", "dark", "system"];
    const storageKey = "benchtrack-theme";
    const colorScheme = window.matchMedia("(prefers-color-scheme: dark)");

    function readSavedTheme() {
        try {
            const saved = localStorage.getItem(storageKey);
            return modes.includes(saved) ? saved : "system";
        } catch (error) {
            console.warn("Unable to read saved theme preference.", error);
            return "system";
        }
    }

    let currentMode = readSavedTheme();

    function resolveTheme(mode) {
        if (mode === "system") {
            return colorScheme.matches ? "dark" : "light";
        }

        return mode;
    }

    function applyTheme() {
        const resolvedTheme = resolveTheme(currentMode);

        root.dataset.theme = resolvedTheme;
        root.style.colorScheme = resolvedTheme;

        themeLabel.textContent =
            currentMode.charAt(0).toUpperCase() + currentMode.slice(1);

        toggleButton.title = `Color theme: ${currentMode}`;

        toggleButton.setAttribute(
            "aria-label",
            `Current theme: ${currentMode}. Activate to change theme.`
        );
    }

    function saveTheme() {
        try {
            localStorage.setItem(storageKey, currentMode);
        } catch (error) {
            console.warn("Unable to save theme preference.", error);
        }
    }

    toggleButton.addEventListener("click", () => {
        const currentIndex = modes.indexOf(currentMode);
        currentMode = modes[(currentIndex + 1) % modes.length];

        saveTheme();
        applyTheme();
    });

    colorScheme.addEventListener("change", () => {
        if (currentMode === "system") {
            applyTheme();
        }
    });

    applyTheme();
})();