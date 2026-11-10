(() => {
  "use strict";

  const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
  const dateFormat = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" });
  const localISODate = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const today = localISODate(new Date());
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHTML = (value = "") => String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
  const makeId = () => `r-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
  const parseState = (raw) => {
    const saved = JSON.parse(raw);
    if (!saved || !Array.isArray(saved.customers) || !Array.isArray(saved.transactions)) throw new Error("Invalid workspace data");
    return { customers: saved.customers, transactions: saved.transactions };
  };
  let profile = null;
  let state = { customers: [], transactions: [] };
  let storageAvailable = true;
  let storageError = "";
  const hasUnassignedLegacyData = false;
  let selectedLedgerId = state.customers[0]?.id || "";
  let toastTimer;

  function showStorageIssue() {
    storageAvailable = false;
    storageError = "KiLedger API is unavailable. Check the backend connection and try again.";
    const blocker = $("#storage-error");
    if (blocker) { blocker.querySelector("p").textContent = storageError; blocker.classList.remove("hidden"); }
  }
  function save() { return true; }
  function displayName() { return profile.name || profile.email.split("@")[0]; }
  function updateNotice() {
    const text = $(".local-notice span:nth-child(2)");
    if (!text) return;
    if (!storageAvailable) {
      text.innerHTML = `<b>Saved data unavailable.</b> ${escapeHTML(storageError)} Use Retry to load it again.`;
      return;
    }
    text.innerHTML = `<b>Signed in as ${escapeHTML(profile.email)}.</b> Business records are loaded from the KiLedger server.`;
  }
  function toast(message) {
    const element = $("#toast");
    element.textContent = message;
    element.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => element.classList.remove("show"), 2600);
  }
  function customerById(id) { return state.customers.find((customer) => customer.id === id); }
  function sortedTransactions(records = state.transactions) { return [...records].sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id)); }
  function getBalance(customerId) {
    return state.transactions.reduce((balance, transaction) => {
      if (transaction.customerId !== customerId) return balance;
      if (transaction.type === "income" && transaction.onCredit) return balance + Number(transaction.amount);
      if (transaction.type === "payment") return balance - Number(transaction.amount);
      return balance;
    }, 0);
  }
  function getDue(customerId) { return Math.max(0, getBalance(customerId)); }
  function dateText(date) {
    if (!date) return "—";
    const parsed = new Date(`${date}T12:00:00`);
    return Number.isNaN(parsed.getTime()) ? "—" : dateFormat.format(parsed);
  }
  function initials(name = "?") { return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); }
  function avatarClass(index) { return `color-${index % 5}`; }
  function customerName(id) { return customerById(id)?.name || (id ? "Removed customer" : "—"); }
  function typeLabel(type) { return type === "expense" ? "Expense" : type === "payment" ? "Payment received" : "Income"; }
  function typeClass(type) { return type === "expense" ? "expense" : type === "payment" ? "payment" : ""; }
  function typeAmount(transaction) {
    return transaction.type === "expense" ? `− ${money.format(transaction.amount)}` : `+ ${money.format(transaction.amount)}`;
  }
  function entryRow(transaction, showMethod = false) {
    const type = transaction.type;
    const icon = type === "expense" ? "↗" : type === "payment" ? "✓" : "↙";
    return `<tr><td><span class="entry-name"><i class="entry-icon ${typeClass(type)}">${icon}</i>${escapeHTML(transaction.description)}</span></td><td>${escapeHTML(customerName(transaction.customerId))}</td><td>${dateText(transaction.date)}</td><td><span class="type-badge ${typeClass(type)}">${typeLabel(type)}</span></td>${showMethod ? `<td>${escapeHTML(transaction.method || "—")}</td>` : ""}<td class="align-right ${type === "expense" ? "amount-negative" : "amount-positive"}">${typeAmount(transaction)}</td></tr>`;
  }
  function changeView(viewName) {
    const names = { dashboard: "Overview", customers: "Customers", transactions: "Transactions", ledger: "Customer ledger", reports: "Reports" };
    if (!names[viewName]) return;
    $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${viewName}`));
    $$(".side-link").forEach((link) => link.classList.toggle("active", link.dataset.view === viewName));
    $("#breadcrumb-current").textContent = names[viewName];
    $("#sidebar").classList.remove("open");
    if (viewName === "ledger") renderLedger();
    if (viewName === "reports") renderReports();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function renderDashboard() {
    const income = state.transactions.filter((transaction) => transaction.type === "payment" || (transaction.type === "income" && !transaction.onCredit)).reduce((total, transaction) => total + Number(transaction.amount), 0);
    const expenses = state.transactions.filter((transaction) => transaction.type === "expense").reduce((total, transaction) => total + Number(transaction.amount), 0);
    const customersDue = state.customers.filter((customer) => getDue(customer.id) > 0);
    const dues = customersDue.reduce((total, customer) => total + getDue(customer.id), 0);
    $("#money-in").textContent = money.format(income);
    $("#money-out").textContent = money.format(expenses);
    $("#outstanding").textContent = money.format(dues);
    $("#due-customers").textContent = customersDue.length;
    $("#customer-total").textContent = state.customers.length;
    $("#customer-nav-count").textContent = state.customers.length;
    $("#profile-name").textContent = displayName();
    $("#profile-email").textContent = profile.email;
    $("#business-name").textContent = profile.businessName || "Business";
    $("#business-initial").textContent = initials(profile.businessName || "Business").slice(0, 1);
    $(".profile-avatar").textContent = initials(displayName()).slice(0, 1);
    $("#greeting-name").textContent = displayName();
    const progress = dues ? Math.min(100, dues / (income + dues || 1) * 100) : 0;
    $("#due-progress").style.width = `${progress}%`;
    renderSparklines();
    const now = new Date();
    $("#today-label").textContent = new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long" }).format(now).toUpperCase();
    renderCashChart();
    const dueList = $("#due-list");
    const topDue = customersDue.sort((a, b) => getDue(b.id) - getDue(a.id)).slice(0, 4);
    dueList.innerHTML = topDue.length ? topDue.map((customer, index) => `<div class="due-row"><i class="customer-avatar ${avatarClass(index)}">${escapeHTML(initials(customer.name))}</i><span class="due-info"><b>${escapeHTML(customer.name)}</b><small>${state.transactions.filter((transaction) => transaction.customerId === customer.id).length} ledger entries</small></span><strong class="due-value">${money.format(getDue(customer.id))}</strong></div>`).join("") : '<div class="due-empty">No outstanding balances. You’re all caught up.</div>';
    $("#recent-transactions").innerHTML = sortedTransactions().slice(0, 5).map((transaction) => entryRow(transaction)).join("") || '<tr><td colspan="5" class="due-empty">No transactions yet. Add your first transaction to see it here.</td></tr>';
  }
  function renderSparklines() {
    const dates = Array.from({ length: 8 }, (_, index) => { const date = new Date(); date.setDate(date.getDate() - (7 - index)); return localISODate(date); });
    const totals = dates.map((date) => state.transactions.filter((transaction) => transaction.date === date).reduce((day, transaction) => {
      if (transaction.type === "expense") day.expense += Number(transaction.amount);
      else if (transaction.type === "payment" || !transaction.onCredit) day.income += Number(transaction.amount);
      return day;
    }, { income: 0, expense: 0 }));
    const max = Math.max(1, ...totals.flatMap((item) => [item.income, item.expense]));
    $("#income-sparkline").innerHTML = totals.map((item) => `<i style="height:${Math.max(2, item.income / max * 100)}%"></i>`).join("");
    $("#expense-sparkline").innerHTML = totals.map((item) => `<i style="height:${Math.max(2, item.expense / max * 100)}%"></i>`).join("");
  }
  function renderCashChart() {
    const dates = Array.from({ length: 7 }, (_, index) => { const date = new Date(); date.setDate(date.getDate() - (6 - index)); return localISODate(date); });
    const totals = dates.map((date) => state.transactions.filter((transaction) => transaction.date === date).reduce((day, transaction) => {
      if (transaction.type === "expense") day.expense += Number(transaction.amount);
      else if (transaction.type === "payment" || !transaction.onCredit) day.income += Number(transaction.amount);
      return day;
    }, { income: 0, expense: 0 }));
    const max = Math.max(1, ...totals.flatMap((item) => [item.income, item.expense]));
    $("#chart-columns").innerHTML = totals.map((item) => `<span class="bar-pair"><i class="income-bar" title="Income ${money.format(item.income)}" style="height:${item.income ? Math.max(3, item.income / max * 100) : 1}%"></i><i class="expense-bar" title="Expenses ${money.format(item.expense)}" style="height:${item.expense ? Math.max(3, item.expense / max * 100) : 1}%"></i></span>`).join("");
    $("#chart-labels").innerHTML = dates.map((date) => `<span>${new Intl.DateTimeFormat("en-IN", { weekday: "short" }).format(new Date(`${date}T12:00:00`))}</span>`).join("");
    const currencyCompact = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", notation: "compact", maximumFractionDigits: 0 });
    $("#chart-y-labels").innerHTML = [1, 0.75, 0.5, 0.25, 0].map((fraction) => `<span>${currencyCompact.format(max * fraction)}</span>`).join("");
    $("#cash-chart-empty").classList.toggle("hidden", totals.some((item) => item.income > 0 || item.expense > 0));
  }
  function renderCustomers() {
    const query = $("#customer-search").value.trim().toLowerCase();
    const records = state.customers.filter((customer) => `${customer.name} ${customer.email} ${customer.phone}`.toLowerCase().includes(query));
    $("#customer-record-count").textContent = `${records.length} ${records.length === 1 ? "customer" : "customers"}`;
    $("#customers-table").innerHTML = records.map((customer, index) => {
      const entries = state.transactions.filter((transaction) => transaction.customerId === customer.id).length;
      const contact = [customer.email, customer.phone].filter(Boolean).map(escapeHTML).join("<br>") || '<span class="muted">No contact details</span>';
      return `<tr><td><span class="entry-name"><i class="customer-avatar ${avatarClass(index)}">${escapeHTML(initials(customer.name))}</i>${escapeHTML(customer.name)}</span></td><td>${contact}</td><td>${dateText(customer.createdAt)}</td><td>${entries}</td><td class="align-right ${getDue(customer.id) > 0 ? "amount-negative" : ""}">${money.format(getDue(customer.id))}</td><td><span class="row-actions"><button data-edit-customer="${escapeHTML(customer.id)}">Edit</button><button data-delete-customer="${escapeHTML(customer.id)}">Delete</button></span></td></tr>`;
    }).join("");
    $("#customers-empty").classList.toggle("hidden", records.length > 0);
    $("#customers-table").parentElement.classList.toggle("hidden", records.length === 0);
    $("#customer-nav-count").textContent = state.customers.length;
    renderTransactionCustomerOptions();
  }
  function renderTransactions() {
    const query = $("#transaction-search").value.trim().toLowerCase();
    const filter = $("#transaction-filter").value;
    const records = sortedTransactions().filter((transaction) => {
      const matchesText = `${transaction.description} ${customerName(transaction.customerId)} ${transaction.method}`.toLowerCase().includes(query);
      const matchesType = filter === "all" || transaction.type === filter;
      return matchesText && matchesType;
    });
    $("#transaction-record-count").textContent = `${records.length} ${records.length === 1 ? "entry" : "entries"}`;
    $("#transactions-table").innerHTML = records.map((transaction) => entryRow(transaction, true)).join("");
    const emptyHeading = $("#transactions-empty h3");
    const emptyCopy = $("#transactions-empty p");
    emptyHeading.textContent = state.transactions.length ? "No matching transactions" : "No transactions yet";
    emptyCopy.textContent = state.transactions.length ? "Try a different search or transaction type." : "Record your first transaction to see it here.";
    $("#transactions-empty").classList.toggle("hidden", records.length > 0);
    $("#transactions-table").parentElement.classList.toggle("hidden", records.length === 0);
  }
  function renderTransactionCustomerOptions() {
    const select = $("#transaction-customer");
    const current = select.value;
    select.innerHTML = '<option value="">No customer</option>' + state.customers.map((customer) => `<option value="${escapeHTML(customer.id)}">${escapeHTML(customer.name)}</option>`).join("");
    if (state.customers.some((customer) => customer.id === current)) select.value = current;
  }
  function renderLedger() {
    const query = $("#ledger-search").value.trim().toLowerCase();
    const records = [...state.customers].filter((customer) => customer.name.toLowerCase().includes(query)).sort((a, b) => getDue(b.id) - getDue(a.id));
    $("#ledger-customer-list").innerHTML = records.map((customer, index) => `<button class="ledger-option ${customer.id === selectedLedgerId ? "selected" : ""}" data-ledger-customer="${escapeHTML(customer.id)}"><i class="customer-avatar ${avatarClass(index)}">${escapeHTML(initials(customer.name))}</i><span><b>${escapeHTML(customer.name)}</b><small>${state.transactions.filter((transaction) => transaction.customerId === customer.id).length} entries</small></span><strong>${money.format(getDue(customer.id))}</strong></button>`).join("") || '<div class="due-empty">No matching customers.</div>';
    const customer = customerById(selectedLedgerId);
    const detail = $("#ledger-detail");
    if (!customer) {
      detail.innerHTML = '<div class="ledger-empty"><span>▤</span><h3>Select a customer account</h3><p>Choose a customer from the list to see their balance and recorded activity.<br />You can add a customer from the Customers page.</p></div>';
      return;
    }
    const recordsForCustomer = sortedTransactions(state.transactions.filter((transaction) => transaction.customerId === customer.id));
    detail.innerHTML = `<div class="ledger-overview"><div class="ledger-customer-title"><i class="customer-avatar">${escapeHTML(initials(customer.name))}</i><span><h2>${escapeHTML(customer.name)}</h2><p>${escapeHTML(customer.email || customer.phone || "Customer account")}</p></span></div><span class="ledger-balance"><small>Outstanding balance</small><strong>${money.format(getDue(customer.id))}</strong></span></div><div class="ledger-actions"><button class="primary-button" data-customer-payment="${escapeHTML(customer.id)}">＋ Record payment</button><button class="secondary-button" data-customer-sale="${escapeHTML(customer.id)}">＋ Add sale</button></div><div class="table-wrap"><table><thead><tr><th>DESCRIPTION</th><th>DATE</th><th>TYPE</th><th class="align-right">AMOUNT</th></tr></thead><tbody>${recordsForCustomer.map((transaction) => {
      const type = transaction.type;
      const signed = type === "expense" ? `− ${money.format(transaction.amount)}` : `+ ${money.format(transaction.amount)}`;
      return `<tr><td>${escapeHTML(transaction.description)}</td><td>${dateText(transaction.date)}</td><td><span class="type-badge ${typeClass(type)}">${typeLabel(type)}${type === "income" && transaction.onCredit ? " · due" : ""}</span></td><td class="align-right ${type === "payment" ? "amount-positive" : type === "income" && transaction.onCredit ? "amount-negative" : ""}">${signed}</td></tr>`;
    }).join("")}</tbody></table></div>${recordsForCustomer.length ? "" : '<div class="ledger-empty"><span>▤</span><h3>No entries yet</h3><p>Record a sale or payment to start this customer’s ledger.</p></div>'}`;
  }
  function renderReports() {
    const period = $("#report-period").value;
    const current = new Date();
    const records = state.transactions.filter((transaction) => {
      if (period === "all") return true;
      const date = new Date(`${transaction.date}T12:00:00`);
      return period === "month" ? date.getFullYear() === current.getFullYear() && date.getMonth() === current.getMonth() : date.getFullYear() === current.getFullYear();
    });
    const income = records.filter((transaction) => transaction.type === "income").reduce((sum, transaction) => sum + Number(transaction.amount), 0);
    const expenses = records.filter((transaction) => transaction.type === "expense").reduce((sum, transaction) => sum + Number(transaction.amount), 0);
    const outstanding = state.customers.reduce((sum, customer) => sum + getDue(customer.id), 0);
    $("#report-income").textContent = money.format(income);
    $("#report-expenses").textContent = money.format(expenses);
    $("#report-net").textContent = money.format(income - expenses);
    $("#report-net").className = income >= expenses ? "amount-positive" : "amount-negative";
    $("#report-outstanding").textContent = money.format(outstanding);
    $("#report-caption").textContent = period === "all" ? `${records.length} recorded entries` : period === "month" ? current.toLocaleDateString("en-IN", { month: "long", year: "numeric" }) : `${current.getFullYear()}`;
    const maximum = Math.max(income, expenses, 1);
    $("#report-bars").innerHTML = `<div class="report-bar-group"><i style="height:${Math.max(2, income / maximum * 100)}%" title="Income ${money.format(income)}"></i><i style="height:${Math.max(2, expenses / maximum * 100)}%" title="Expenses ${money.format(expenses)}"></i><span>Recorded period</span></div>`;
    const topCustomers = [...state.customers].map((customer) => ({ customer, due: getDue(customer.id) })).filter((item) => item.due > 0).sort((a, b) => b.due - a.due).slice(0, 5);
    $("#report-customer-list").innerHTML = topCustomers.map((item, index) => `<div class="report-customer-item"><i class="customer-avatar ${avatarClass(index)}">${escapeHTML(initials(item.customer.name))}</i><span>${escapeHTML(item.customer.name)}</span><strong>${money.format(item.due)}</strong></div>`).join("") || '<div class="due-empty">No outstanding customer balances.</div>';
  }
  function renderAll() {
    if (!storageAvailable) { $("#storage-error p").textContent = storageError; $("#storage-error").classList.remove("hidden"); return; }
    updateNotice();
    renderDashboard(); renderCustomers(); renderTransactions();
    if ($("#view-ledger").classList.contains("active")) renderLedger();
    if ($("#view-reports").classList.contains("active")) renderReports();
  }
  function openCustomer(customer) {
    const form = $("#customer-form");
    form.reset();
    form.elements.customerId.value = customer?.id || "";
    form.elements.name.value = customer?.name || "";
    form.elements.email.value = customer?.email || "";
    form.elements.phone.value = customer?.phone || "";
    form.elements.notes.value = customer?.notes || "";
    $("#customer-modal-title").textContent = customer ? "Edit customer" : "Add a customer";
    $("#save-customer").textContent = customer ? "Save changes" : "Save customer";
    $("#customer-dialog").showModal();
  }
  function openTransaction({ customerId = "", type = "income", credit = false } = {}) {
    const form = $("#transaction-form");
    form.reset();
    renderTransactionCustomerOptions();
    form.elements.type.value = type;
    form.elements.customerId.value = customerId;
    form.elements.date.value = today;
    form.elements.onCredit.checked = credit;
    form.elements.onCredit.disabled = type !== "income";
    form.elements.description.placeholder = type === "payment" ? "e.g. Payment received" : type === "expense" ? "e.g. Rent, supplies, courier" : "e.g. Product sale, service";
    $("#transaction-dialog").showModal();
  }
  $$(".side-link").forEach((link) => link.addEventListener("click", () => changeView(link.dataset.view)));
  $$('[data-navigate]').forEach((button) => button.addEventListener("click", () => changeView(button.dataset.navigate)));
  $$('[data-open-customer]').forEach((button) => button.addEventListener("click", () => openCustomer()));
  $$('[data-open-transaction]').forEach((button) => button.addEventListener("click", () => openTransaction()));
  $("#customer-search").addEventListener("input", renderCustomers);
  $("#transaction-search").addEventListener("input", renderTransactions);
  $("#transaction-filter").addEventListener("change", renderTransactions);
  $("#ledger-search").addEventListener("input", renderLedger);
  $("#report-period").addEventListener("change", renderReports);
  $("#mobile-menu").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  $("#retry-storage").addEventListener("click", () => window.location.reload());
  $("#dismiss-notice").addEventListener("click", () => $(".local-notice").remove());
  $("#help-button").addEventListener("click", () => window.alert("Your account and business records are served by the KiLedger API. Use HTTPS when hosting outside your computer."));
  [$("#sign-out"), $("#sign-out-top"), $("#sign-out-topbar")].forEach((link) => link.addEventListener("click", async (event) => {
    event.preventDefault();
    try { await KiLedgerAPI.logout(); } catch { /* An expired session is already signed out. */ }
    window.location.href = "login.html";
  }));
  $("#print-report").addEventListener("click", () => window.print());

  $("#customers-table").addEventListener("click", async (event) => {
    const editButton = event.target.closest("[data-edit-customer]");
    const deleteButton = event.target.closest("[data-delete-customer]");
    if (editButton) openCustomer(customerById(editButton.dataset.editCustomer));
    if (deleteButton) {
      const customer = customerById(deleteButton.dataset.deleteCustomer);
      if (!customer || !window.confirm(`Delete ${customer.name}? Related transactions will remain, marked as a removed customer.`)) return;
      try {
        await KiLedgerAPI.archiveCustomer(customer.id);
        state.customers = state.customers.filter((record) => record.id !== customer.id);
        if (selectedLedgerId === customer.id) selectedLedgerId = state.customers[0]?.id || "";
        renderAll(); toast("Customer archived.");
      } catch (error) { toast(error.message); }
    }
  });
  $("#ledger-customer-list").addEventListener("click", (event) => {
    const option = event.target.closest("[data-ledger-customer]");
    if (option) { selectedLedgerId = option.dataset.ledgerCustomer; renderLedger(); }
  });
  $("#ledger-detail").addEventListener("click", (event) => {
    const payment = event.target.closest("[data-customer-payment]");
    const sale = event.target.closest("[data-customer-sale]");
    if (payment) openTransaction({ customerId: payment.dataset.customerPayment, type: "payment" });
    if (sale) openTransaction({ customerId: sale.dataset.customerSale, type: "income", credit: true });
  });
  $("#customer-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const customerId = form.elements.customerId.value;
    const previous = customerById(customerId);
    const payload = { name: form.elements.name.value.trim(), email: form.elements.email.value.trim() || null, phone: form.elements.phone.value.trim() || null, notes: form.elements.notes.value.trim() };
    try {
      const customer = previous ? await KiLedgerAPI.updateCustomer(customerId, payload) : await KiLedgerAPI.createCustomer(payload);
      if (previous) state.customers = state.customers.map((item) => item.id === customerId ? customer : item);
      else state.customers.push(customer);
      selectedLedgerId = customer.id;
      $("#customer-dialog").close(); renderAll(); toast(previous ? "Customer updated." : "Customer added.");
    } catch (error) { toast(error.message); }
  });
  $("#transaction-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const type = form.elements.type.value;
    const customerId = form.elements.customerId.value;
    const onCredit = type === "income" && form.elements.onCredit.checked;
    if (onCredit && !customerId) { toast("Choose a customer for an unpaid sale."); form.elements.customerId.focus(); return; }
    const amountInput = form.elements.amount.value;
    const amount = Number(amountInput);
    if (!Number.isFinite(amount) || amount <= 0) { toast("Enter an amount greater than zero."); return; }
    if (type === "payment" && customerId && amount > getDue(customerId)) {
      const excess = amount - getDue(customerId);
      if (!window.confirm(`This payment is ${money.format(excess)} more than the current balance due. Record it anyway?`)) return;
    }
    try {
      const transaction = await KiLedgerAPI.createTransaction({ description: form.elements.description.value.trim(), amount_minor: KiLedgerAPI.toMinor(amountInput), currency: "INR", type, customer_id: customerId || null, date: form.elements.date.value, method: form.elements.method.value, on_credit: onCredit }, crypto.randomUUID());
      state.transactions.push(transaction); $("#transaction-dialog").close(); renderAll(); toast("Transaction recorded.");
    } catch (error) { toast(error.message); }
  });
  $("#transaction-form").elements.onCredit.addEventListener("change", (event) => {
    const type = $("#transaction-form").elements.type.value;
    if (event.target.checked && type !== "income") event.target.checked = false;
  });
  $$("#transaction-form input[name='type']").forEach((radio) => radio.addEventListener("change", () => {
    const checkbox = $("#transaction-form").elements.onCredit;
    checkbox.disabled = radio.value !== "income";
    if (radio.value !== "income") checkbox.checked = false;
    if (radio.value === "payment") $("#transaction-form").elements.description.placeholder = "e.g. Payment received";
    else $("#transaction-form").elements.description.placeholder = radio.value === "expense" ? "e.g. Rent, supplies, courier" : "e.g. Product sale, service";
  }));

  (async () => {
    try {
      const result = await KiLedgerAPI.bootstrap();
      profile = result.profile;
      state = result.state;
      selectedLedgerId = state.customers[0]?.id || "";
      updateNotice();
      renderAll();
    } catch (error) {
      if (error.status === 401) { window.location.replace("login.html"); return; }
      storageAvailable = false;
      storageError = error.message;
      showStorageIssue();
    }
  })();
})();
