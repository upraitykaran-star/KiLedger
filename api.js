(() => {
  "use strict";
  const base = window.KILEDGER_API_BASE;
  let csrf = "";
  async function request(path, options = {}) {
    const method = options.method || "GET";
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (csrf && !["GET", "HEAD", "OPTIONS"].includes(method)) headers["X-CSRF-Token"] = csrf;
    let response;
    try {
      response = await fetch(`${base}${path}`, { ...options, method, headers, credentials: "include" });
    } catch {
      throw new Error("KiLedger API is unavailable. Start the backend and try again.");
    }
    if (response.status === 204) return null;
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(typeof body.detail === "string" ? body.detail : "The request could not be completed.");
      error.status = response.status;
      throw error;
    }
    if (body.csrf_token) csrf = body.csrf_token;
    return body;
  }
  const json = (method, payload, headers) => ({ method, body: JSON.stringify(payload), headers });
  const listAll = async (path) => {
    const output = [];
    let page = 1;
    while (true) {
      const result = await request(`${path}${path.includes("?") ? "&" : "?"}page=${page}&page_size=100`);
      output.push(...result.items);
      if (output.length >= result.total || !result.items.length) return output;
      page += 1;
    }
  };
  const toMinor = (value) => {
    const text = String(value).trim();
    if (!/^\d+(\.\d{1,2})?$/.test(text)) throw new Error("Enter an amount with up to two decimal places.");
    const [rupees, paise = ""] = text.split(".");
    return Number(rupees) * 100 + Number(paise.padEnd(2, "0"));
  };
  const fromMinor = (value) => Number(value) / 100;
  const customer = (item) => ({ ...item, id: item.id, createdAt: String(item.created_at || "").slice(0, 10) });
  const transaction = (item) => ({ ...item, id: item.id, amount: fromMinor(item.amount_minor), customerId: item.customer_id || "", onCredit: item.on_credit, createdAt: item.created_at });
  window.KiLedgerAPI = {
    request, json, listAll, toMinor,
    async bootstrap() {
      const me = await request("/auth/me");
      const [customers, transactions] = await Promise.all([listAll("/customers"), listAll("/transactions")]);
      return { profile: { id: me.user.id, name: me.user.name, email: me.user.email, businessId: me.business.id, businessName: me.business.name, role: me.role },
        state: { customers: customers.map(customer), transactions: transactions.map(transaction) } };
    },
    async login(payload) { return request("/auth/login", json("POST", payload)); },
    async register(payload) { return request("/auth/register", json("POST", payload)); },
    async logout() { return request("/auth/logout", { method: "POST" }); },
    async createCustomer(payload) { return customer(await request("/customers", json("POST", payload))); },
    async updateCustomer(id, payload) { return customer(await request(`/customers/${encodeURIComponent(id)}`, json("PATCH", payload))); },
    async archiveCustomer(id) { return request(`/customers/${encodeURIComponent(id)}`, { method: "DELETE" }); },
    async createTransaction(payload, idempotencyKey) { return transaction(await request("/transactions", json("POST", payload, { "Idempotency-Key": idempotencyKey }))); },
  };
})();
