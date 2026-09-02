/* Paltoo SPA — zero build step, mobile-first. */
const API = "/api";
const state = {
  token: localStorage.getItem("plt_token") || "",
  user: JSON.parse(localStorage.getItem("plt_user") || "null"),
  vaccineOptions: null,
  selectedVet: null,
  selectedDate: "",
  selectedSlot: "",
};

const $ = (sel) => document.querySelector(sel);
const view = () => $("#view");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast show" + (isErr ? " err" : "");
  clearTimeout(t._h);
  t._h = setTimeout(() => (t.className = "toast"), 2800);
}

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(API + path, { ...opts, headers });
  if (res.status === 401 && state.token) { logout(false); }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Something went wrong");
  return data;
}

function saveAuth(token, user) {
  state.token = token; state.user = user;
  localStorage.setItem("plt_token", token);
  localStorage.setItem("plt_user", JSON.stringify(user));
}
function logout(show = true) {
  state.token = ""; state.user = null;
  localStorage.removeItem("plt_token"); localStorage.removeItem("plt_user");
  if (show) toast("Logged out. See you soon! 👋");
  render();
}
function setTopbar() {
  const chip = $("#userChip"), btn = $("#logoutBtn");
  if (state.user) { chip.classList.remove("hidden"); chip.textContent = `${esc(state.user.name)} · ${esc(state.user.role)}`; btn.classList.remove("hidden"); }
  else { chip.classList.add("hidden"); btn.classList.add("hidden"); }
}

function fmtDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}
function todayIso() { return new Date().toISOString().slice(0, 10); }
function addDaysIso(days) {
  const d = new Date(); d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

/* ============================= RENDER ============================= */

function render() {
  setTopbar();
  if (!state.user) return renderLanding();
  if (state.user.role === "vet") return renderVetDash();
  if (state.user.role === "owner") return renderOwnerDash();
  renderAdminDash();
}

/* ---------- LANDING ---------- */
async function renderLanding() {
  let stats = { vets: 0, verified_vets: 0, pets: 0, appointments_total: 0, appointments_today: 0, cities: 0 };
  try { stats = await api("/stats"); } catch (e) {}
  view().innerHTML = `
    <section class="hero">
      <div class="logo-big">🐶🐱</div>
      <h1>Pet care jo <em>kabhi miss</em> na ho.</h1>
      <p>Paltoo pe apne pet ko register karo, vaccinations track karo, reminders pao, aur verified vets se online appointment book karo — sab kuch phone se.</p>
      <div class="hero-cta">
        <button class="btn" onclick="goRegister()">Get started free</button>
        <button class="btn ghost" onclick="goLogin()">I already have an account</button>
      </div>
    </section>
    <div class="stats-row">
      <div class="stat"><b>${stats.verified_vets}</b><span>Verified vets</span></div>
      <div class="stat"><b>${stats.pets}</b><span>Happy pets</span></div>
      <div class="stat"><b>${stats.appointments_total}</b><span>Appointments</span></div>
    </div>
    <h2 class="section-title">Find a vet near you</h2>
    <div id="vetList">${loadingCard()}</div>`;
  loadPublicVets("");
}

async function loadPublicVets(city) {
  try {
    const q = city ? `?city=${encodeURIComponent(city)}` : "";
    const vets = await api("/vets" + q);
    const el = $("#vetList");
    if (!el) return;
    el.innerHTML = vets.length
      ? vets.map(vetCard).join("")
      : `<div class="empty"><div class="big">🩺</div>No vets in this city yet.</div>`;
    attachSlotButtons();
  } catch (e) { toast(e.message, true); }
}

function vetCard(v) {
  return `<div class="card">
    <div class="card-row">
      <div>
        <h3>${esc(v.clinic_name)}</h3>
        <div class="sub">${esc(v.owner.name)} · ${esc(v.specialty)}</div>
        <div class="meta">📍 ${esc(v.owner.city)} · ${esc(v.address)}</div>
        <div class="meta">💵 Rs ${v.fee_pkr} consultation · ⭐ ${v.verified ? "Verified" : ""}</div>
      </div>
      <button class="btn small" data-vet="${v.user_id}" data-clinic="${esc(v.clinic_name)}">Book</button>
    </div>
    <div id="slots-${v.user_id}" class="mt-16"></div>
  </div>`;
}

function attachSlotButtons() {
  document.querySelectorAll("[data-vet]").forEach((b) =>
    b.addEventListener("click", () => {
      if (!state.user) { toast("Login karo pehle — 10 second ka kaam hai 😊"); goLogin(); return; }
      if (state.user.role !== "owner") { toast("Only pet owners can book appointments"); return; }
      openBooking(b.dataset.vet, b.dataset.clinic);
    })
  );
}

function loadingCard() { return `<div class="empty"><div class="big">⏳</div>Loading…</div>`; }

/* ---------- AUTH ---------- */
function goLogin() { view().innerHTML = authForm("login"); bindAuth("login"); }
function goRegister() { view().innerHTML = authForm("register"); bindAuth("register"); }

function authForm(mode) {
  const reg = mode === "register";
  return `
    <div class="card mt-16">
      <h2 style="margin-bottom:4px">${reg ? "Create your account" : "Welcome back"}</h2>
      <p class="sub" style="margin-bottom:16px">${reg ? "Free forever — apne pet ko register karo aur booking shuru karo." : "Login to manage pets, vaccines & appointments."}</p>
      ${reg ? `<div class="field"><label>I am a…</label><select id="f_role">
        <option value="owner">🐾 Pet owner</option><option value="vet">🩺 Vet / clinic</option></select></div>` : ""}
      <div class="field"><label>Email</label><input id="f_email" type="email" placeholder="you@example.com"></div>
      <div class="field"><label>Password</label><input id="f_pass" type="password" placeholder="${reg ? "8+ chars with a number" : "••••••••"}"></div>
      ${reg ? `
        <div class="grid2">
          <div class="field"><label>Full name</label><input id="f_name" placeholder="Ayesha Khan"></div>
          <div class="field"><label>City</label><input id="f_city" placeholder="Karachi"></div>
        </div>
        <div class="field"><label>Phone</label><input id="f_phone" placeholder="0300-1234567"></div>
      ` : ""}
      <button class="btn" style="width:100%" id="submitBtn">${reg ? "Create account" : "Login"}</button>
      <p class="small muted" style="margin-top:14px;text-align:center">
        ${reg ? "Already have an account?" : "New to Paltoo?"}
        <a href="#" onclick="event.preventDefault();${reg ? "goLogin()" : "goRegister()"}">${reg ? "Login" : "Register"}</a>
      </p>
    </div>`;
}

function bindAuth(mode) {
  $("#submitBtn").addEventListener("click", async () => {
    const email = $("#f_email").value.trim(), pass = $("#f_pass").value;
    const btn = $("#submitBtn");
    if (!email || !pass) return toast("Email aur password dono chahiye", true);
    btn.disabled = true; btn.textContent = "Please wait…";
    try {
      if (mode === "login") {
        const body = new URLSearchParams({ username: email, password: pass });
        const res = await fetch(API + "/auth/login", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Login failed");
        saveAuth(data.access_token, data.user);
        toast(`Welcome back, ${data.user.name}! 🎉`);
      } else {
        const data = await api("/auth/register", { method: "POST", body: JSON.stringify({
          email, password: pass, name: $("#f_name").value.trim(), city: $("#f_city").value.trim(),
          phone: $("#f_phone").value.trim(), role: $("#f_role").value }) });
        saveAuth(data.access_token, data.user);
        toast("Account created — welcome to Paltoo! 🐾");
      }
      render();
    } catch (e) { toast(e.message, true); btn.disabled = false; btn.textContent = mode === "login" ? "Login" : "Create account"; }
  });
}

/* ---------- OWNER DASHBOARD ---------- */
async function renderOwnerDash() {
  view().innerHTML = `
    <div class="tabs">
      <div class="tab active" data-tab="pets">My pets</div>
      <div class="tab" data-tab="appts">Appointments</div>
      <div class="tab" data-tab="book">Book a vet</div>
    </div>
    <div id="tabContent"><div class="empty"><div class="big">⏳</div>Loading…</div></div>`;
  document.querySelectorAll(".tab").forEach((t) =>
    t.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      ownerTab(t.dataset.tab);
    })
  );
  ownerTab("pets");
}

async function ownerTab(tab) {
  const c = $("#tabContent"); if (!c) return;
  if (tab === "pets") return ownerPetsView();
  if (tab === "appts") return ownerApptsView();
  ownerBookView();
}

async function ownerPetsView() {
  const c = $("#tabContent");
  try {
    const pets = await api("/pets");
    c.innerHTML = `
      <button class="btn" onclick="addPetForm()">+ Add a pet</button>
      <div class="mt-16" id="petArea">${pets.length ? pets.map(petSummaryCard).join("") : emptyBox("🐶", "No pets yet", "Apna pehla pet add karo aur vaccine reminders start karo.")}</div>`;
  } catch (e) { toast(e.message, true); }
}

function petSummaryCard(p) {
  return `<div class="card" style="cursor:pointer" onclick="petDetail(${p.id})">
    <div class="card-row">
      <div>
        <h3>${esc(p.name)} ${p.species === "dog" ? "🐕" : p.species === "cat" ? "🐈" : "🐾"}</h3>
        <div class="sub">${esc(p.breed || p.species)} · ${p.gender} · ${p.age_years} yrs · ${p.weight_kg} kg</div>
      </div>
      <span class="pill gray">View →</span>
    </div>
  </div>`;
}

async function addPetForm() {
  const c = $("#tabContent");
  c.innerHTML = `
    <button class="back" onclick="ownerPetsView()">← My pets</button>
    <div class="card mt-8">
      <h3>Add a new pet</h3>
      <div class="mt-8 field"><label>Name</label><input id="p_name" placeholder="Tommy"></div>
      <div class="grid2">
        <div class="field"><label>Species</label><select id="p_species"><option value="dog">Dog</option><option value="cat">Cat</option><option value="other">Other</option></select></div>
        <div class="field"><label>Gender</label><select id="p_gender"><option value="male">Male</option><option value="female">Female</option></select></div>
      </div>
      <div class="grid2">
        <div class="field"><label>Breed (optional)</label><input id="p_breed" placeholder="Golden Retriever"></div>
        <div class="field"><label>Weight (kg)</label><input id="p_weight" type="number" step="0.1" value="5"></div>
      </div>
      <div class="field"><label>Birth date</label><input id="p_birth" type="date" max="${todayIso()}"></div>
      <div class="field"><label>Medical conditions (optional)</label><textarea id="p_conditions" placeholder="None"></textarea></div>
      <button class="btn" style="width:100%" id="savePetBtn">Save pet</button>
    </div>`;
  $("#savePetBtn").addEventListener("click", async () => {
    try {
      await api("/pets", { method: "POST", body: JSON.stringify({
        name: $("#p_name").value.trim(), species: $("#p_species").value, gender: $("#p_gender").value,
        breed: $("#p_breed").value.trim(), weight_kg: parseFloat($("#p_weight").value) || 1,
        birth_date: $("#p_birth").value, medical_conditions: $("#p_conditions").value.trim() }) });
      toast("Pet added! 🎉"); ownerPetsView();
    } catch (e) { toast(e.message, true); }
  });
}

async function petDetail(id) {
  const c = $("#tabContent");
  try {
    const d = await api(`/pets/${id}`);
    const p = d.pet;
    const badges = { overdue: "red", due: "amber", upcoming: "teal", covered: "gray" };
    c.innerHTML = `
      <button class="back" onclick="ownerPetsView()">← My pets</button>
      <div class="card mt-8">
        <div class="card-row">
          <h3>${esc(p.name)} ${p.species === "dog" ? "🐕" : p.species === "cat" ? "🐈" : "🐾"}</h3>
          <button class="btn danger small" onclick="deletePet(${p.id})">Delete</button>
        </div>
        <div class="meta">${esc(p.breed || p.species)} · ${p.gender} · born ${fmtDate(p.birth_date)} · ${p.weight_kg} kg</div>
        ${p.medical_conditions ? `<div class="meta">⚠️ ${esc(p.medical_conditions)}</div>` : ""}
      </div>
      <h2 class="section-title">💉 Vaccine schedule</h2>
      ${d.reminders.length ? d.reminders.map((r) => `
        <div class="reminder">
          <div><div class="rname">${esc(r.name)}</div><div class="rdate">due ${fmtDate(r.due_date)}</div></div>
          <div class="right"><span class="pill ${badges[r.status] || "gray"}">${r.status}</span></div>
        </div>`).join("") : emptyBox("💉", "No vaccines tracked yet")}
      <h2 class="section-title">Log a vaccination</h2>
      <div class="card">
        <div class="field"><label>Vaccine</label><select id="v_key"></select></div>
        <div class="field"><label>Date given</label><input id="v_date" type="date" max="${todayIso()}"></div>
        <button class="btn small" id="v_btn">Log dose</button>
      </div>`;
    const opts = state.vaccineOptions || (state.vaccineOptions = await api("/vaccines/options"));
    const list = (opts.find((o) => o.species === p.species) || { vaccines: [] }).vaccines;
    const sel = $("#v_key");
    sel.innerHTML = list.map((v) => `<option value="${v.key}">${esc(v.name)}</option>`).join("");
    $("#v_date").value = todayIso();
    $("#v_btn").addEventListener("click", async () => {
      try {
        await api(`/pets/${id}/vaccines`, { method: "POST", body: JSON.stringify({ vaccine_key: sel.value, administered_on: $("#v_date").value }) });
        toast("Dose logged! 💉"); petDetail(id);
      } catch (e) { toast(e.message, true); }
    });
  } catch (e) { toast(e.message, true); }
}

async function deletePet(id) {
  if (!confirm("Delete this pet and all records?")) return;
  try { await api(`/pets/${id}`, { method: "DELETE" }); toast("Pet removed"); ownerPetsView(); }
  catch (e) { toast(e.message, true); }
}

async function ownerApptsView() {
  const c = $("#tabContent");
  try {
    const appts = await api("/appointments?upcoming_only=true");
    c.innerHTML = `<h2 class="section-title">Upcoming appointments</h2>
      ${appts.length ? appts.map(apptCard).join("") : emptyBox("📅", "No upcoming appointments", "Book a vet from the 'Book a vet' tab.")}`;
    document.querySelectorAll("[data-cancel]").forEach((b) =>
      b.addEventListener("click", async () => { try { await api(`/appointments/${b.dataset.cancel}/cancel`, { method: "POST" }); toast("Cancelled — slot freed up"); ownerApptsView(); } catch (e) { toast(e.message, true); } })
    );
  } catch (e) { toast(e.message, true); }
}

function apptCard(a) {
  const st = { confirmed: "green", pending: "amber", completed: "gray", cancelled: "red", no_show: "gray" };
  return `<div class="card">
    <div class="card-row">
      <div>
        <h3>${esc(a.pet.name)} → ${esc(a.vet.name)}</h3>
        <div class="sub">${fmtDate(a.date)} at ${a.slot} · ${esc(a.reason)}</div>
        <div class="meta">#${esc(a.ref)} · ${esc(a.vet.city)}</div>
      </div>
      <span class="pill ${st[a.status] || "gray"}">${a.status}</span>
    </div>
    ${a.status === "confirmed" || a.status === "pending" ? `<button class="btn danger small mt-8" data-cancel="${a.id}">Cancel</button>` : ""}
  </div>`;
}

/* ---------- BOOKING ---------- */
async function openBooking(vetId, clinicName) {
  const pets = await api("/pets").catch(() => []);
  if (!pets.length) { toast("Pehle ek pet add karo 😊"); ownerTab("pets"); return; }
  state.selectedVet = { id: vetId, name: clinicName }; state.selectedDate = addDaysIso(1); state.selectedSlot = "";
  view().innerHTML = `
    <button class="back" onclick="render()">← Dashboard</button>
    <div class="card mt-8">
      <h3>📅 Book at ${esc(clinicName)}</h3>
      <div class="mt-16 field"><label>Pet</label><select id="b_pet">${pets.map((p) => `<option value="${p.id}">${esc(p.name)} (${p.species})</option>`).join("")}</select></div>
      <div class="field"><label>Reason (optional)</label><input id="b_reason" placeholder="Vaccination / checkup / not feeling well"></div>
      <div class="field"><label>Date</label><input id="b_date" type="date" min="${todayIso()}" max="${addDaysIso(14)}" value="${state.selectedDate}"></div>
      <div class="field"><label>Available slots</label><div id="b_slots" class="slots">—</div></div>
      <button class="btn" style="width:100%" id="b_book" disabled>Book appointment</button>
    </div>`;
  $("#b_date").addEventListener("change", loadSlots);
  $("#b_slots").addEventListener("click", (ev) => {
    const chip = ev.target.closest(".slot-chip");
    if (!chip || chip.disabled) return;
    document.querySelectorAll(".slot-chip").forEach((x) => x.classList.remove("sel"));
    chip.classList.add("sel");
    state.selectedSlot = chip.dataset.slot;
    $("#b_book").disabled = false;
  });
  $("#b_book").addEventListener("click", bookNow);
  loadSlots();
}

async function loadSlots() {
  const date = $("#b_date").value;
  if (!date) return;
  state.selectedDate = date; state.selectedSlot = "";
  const box = $("#b_slots"); if (!box) return;
  box.innerHTML = `<div class="muted small">Loading…</div>`;
  try {
    const res = await api(`/vets/${state.selectedVet.id}/slots?date=${date}`);
    if (!res.slots.length) box.innerHTML = `<div class="muted small">No free slots this day — pick another date.</div>`;
    else box.innerHTML = res.slots.map((s) => `<button class="slot-chip" data-slot="${s}">${s}</button>`).join("");
    $("#b_book").disabled = true;
  } catch (e) { box.innerHTML = `<div class="muted small">${esc(e.message)}</div>`; }
}

async function bookNow() {
  try {
    const data = await api("/appointments", { method: "POST", body: JSON.stringify({
      vet_id: state.selectedVet.id, pet_id: parseInt($("#b_pet").value),
      date: state.selectedDate, slot: state.selectedSlot, reason: $("#b_reason").value.trim() || "General checkup" }) });
    toast(`Booked! Ref ${data.ref} 🎉`); render();
  } catch (e) { toast(e.message, true); }
}

async function ownerBookView() {
  const c = $("#tabContent");
  c.innerHTML = `<h2 class="section-title">Verified vets</h2>
    <div class="field"><label>Search by city</label><input id="citySearch" placeholder="Karachi, Lahore, Islamabad…"></div>
    <div id="vetList2"><div class="empty"><div class="big">⏳</div>Loading…</div></div>`;
  const load = async () => {
    try {
      const vets = await api(`/vets${$("#citySearch").value.trim() ? "?city=" + encodeURIComponent($("#citySearch").value.trim()) : ""}`);
      $("#vetList2").innerHTML = vets.length ? vets.map(vetCard).join("") : `<div class="empty"><div class="big">🩺</div>No vets found.</div>`;
      attachSlotButtons();
    } catch (e) { toast(e.message, true); }
  };
  $("#citySearch").addEventListener("input", debounce(load, 400));
  load();
}
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

/* ---------- VET DASHBOARD ---------- */
async function renderVetDash() {
  view().innerHTML = `
    <div class="tabs">
      <div class="tab active" data-vtab="appts">Today's visits</div>
      <div class="tab" data-vtab="profile">My clinic</div>
    </div>
    <div id="vtabContent"><div class="empty"><div class="big">⏳</div>Loading…</div></div>`;
  document.querySelectorAll(".tab").forEach((t) =>
    t.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      t.classList.add("active"); vetTab(t.dataset.vtab);
    })
  );
  vetTab("appts");
}

async function vetTab(tab) {
  const c = $("#vtabContent"); if (!c) return;
  if (tab === "profile") return vetProfileView();
  try {
    const appts = await api("/me/vet/appointments?date=" + todayIso());
    c.innerHTML = `<h2 class="section-title">Today · ${fmtDate(todayIso())}</h2>
      ${appts.length ? appts.map((a) => vetApptCard(a)).join("") : emptyBox("🩺", "No appointments today", "Kal ke liye calendar check karo ya profile tab me fee update karo.")}`;
    document.querySelectorAll("[data-vstatus]").forEach((b) =>
      b.addEventListener("click", async () => {
        const { id, status } = b.dataset;
        try { await api(`/me/vet/appointments/${id}/status?new_status=${status}`, { method: "POST" }); toast("Updated"); vetTab("appts"); }
        catch (e) { toast(e.message, true); }
      })
    );
  } catch (e) { toast(e.message, true); }
}

function vetApptCard(a) {
  const st = { confirmed: "green", pending: "amber", completed: "gray", cancelled: "red", no_show: "gray" };
  const canDo = a.status === "confirmed"
    ? `<button class="btn small" data-vstatus='{"id":${a.id},"status":"completed"}'>Mark completed</button> <button class="btn danger small" data-vstatus='{"id":${a.id},"status":"no_show"}'>No-show</button>`
    : "";
  return `<div class="card">
    <div class="card-row">
      <div>
        <h3>${esc(a.pet.name)} ${a.pet.species === "dog" ? "🐕" : "🐈"}</h3>
        <div class="sub">${a.slot} · ${esc(a.reason)} · ${esc(a.pet.breed || a.pet.species)}</div>
        <div class="meta">#${esc(a.ref)}</div>
      </div>
      <span class="pill ${st[a.status] || "gray"}">${a.status}</span>
    </div>
    <div class="mt-8">${canDo}</div>
  </div>`;
}

async function vetProfileView() {
  const c = $("#vtabContent");
  try {
    const p = await api("/me/vet-profile");
    c.innerHTML = `<div class="card mt-8">
      <h3>🩺 My clinic</h3>
      <div class="field mt-16"><label>Clinic name</label><input id="vp_clinic" value="${esc(p.clinic_name)}"></div>
      <div class="field"><label>Specialty</label><input id="vp_spec" value="${esc(p.specialty)}"></div>
      <div class="field"><label>Address</label><input id="vp_addr" value="${esc(p.address)}"></div>
      <div class="field"><label>Fee (PKR)</label><input id="vp_fee" type="number" value="${p.fee_pkr}"></div>
      <div class="field"><label>Bio</label><textarea id="vp_bio">${esc(p.bio)}</textarea></div>
      <button class="btn" id="vp_save">Save profile</button>
      <p class="small muted mt-8">${p.verified ? "✅ Verified — visible in the public directory" : "⏳ Pending verification — admin approval ke baad directory me aaoge"}</p>
    </div>`;
    $("#vp_save").addEventListener("click", async () => {
      try {
        await api("/me/vet-profile", { method: "PATCH", body: JSON.stringify({
          clinic_name: $("#vp_clinic").value.trim(), specialty: $("#vp_spec").value.trim(),
          address: $("#vp_addr").value.trim(), fee_pkr: parseInt($("#vp_fee").value) || 0, bio: $("#vp_bio").value.trim() }) });
        toast("Profile updated ✅"); vetProfileView();
      } catch (e) { toast(e.message, true); }
    });
  } catch (e) { toast(e.message, true); }
}

/* ---------- ADMIN (minimal) ---------- */
async function renderAdminDash() {
  view().innerHTML = `
    <h2 class="section-title">Admin · Verify vets</h2>
    <div id="adminList"><div class="empty"><div class="big">⏳</div>Loading…</div></div>`;
  try {
    const vets = await api("/admin/vets");
    $("#adminList").innerHTML = vets.length ? vets.map((v) => `
      <div class="card">
        <div class="card-row">
          <div><h3>${esc(v.clinic_name)}</h3>
          <div class="sub">${esc(v.owner.name)} · ${esc(v.owner.city)}</div></div>
          <span class="pill ${v.verified ? "green" : "amber"}">${v.verified ? "verified" : "pending"}</span>
        </div>
        ${v.verified ? "" : `<button class="btn small mt-8" data-verify="${v.id}">✓ Verify</button>`}
      </div>`).join("") : emptyBox("🛡️", "No vet profiles");
    document.querySelectorAll("[data-verify]").forEach((b) =>
      b.addEventListener("click", async () => { try { await api(`/admin/vets/${b.dataset.verify}/verify`, { method: "POST" }); toast("Verified ✅"); renderAdminDash(); } catch (e) { toast(e.message, true); } })
    );
  } catch (e) { toast(e.message, true); }
}

function emptyBox(icon, title, sub = "") {
  return `<div class="empty"><div class="big">${icon}</div><b>${esc(title)}</b>${sub ? `<p class="small mt-8">${esc(sub)}</p>` : ""}</div>`;
}

/* ============================= BOOT ============================= */
(function boot() {
  setTopbar();
  render();
})();
