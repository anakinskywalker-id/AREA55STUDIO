import { PanoViewer } from './pano-viewer.js';

const loginScreen = document.getElementById('login-screen');
const adminDashboard = document.getElementById('admin-dashboard');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const toastEl = document.getElementById('toast');

let state = { projects: [] };
let activeProjectIdx = 0;
let activeRoomIdx = -1;
let editorViewer = null;

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  setTimeout(() => toastEl.classList.remove('show'), 2800);
}

function slugify(str) {
  return String(str || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'projek-' + Date.now();
}

function resolveAssetUrl(path) {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
    return path;
  }
  return path.replace(/^\/+/, '');
}

function getActiveProject() {
  return state.projects[activeProjectIdx] || null;
}

function getActiveRoom() {
  const proj = getActiveProject();
  if (!proj || !proj.rooms) return null;
  return proj.rooms[activeRoomIdx] || null;
}

// ---------- Auth ----------
async function checkAuth() {
  try {
    const res = await fetch('/api/auth-check');
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated) {
        await enterDashboard();
        return;
      }
    }
  } catch {
    // ignore
  }
  loginScreen.style.display = 'grid';
  adminDashboard.style.display = 'none';
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.style.display = 'none';
  const password = document.getElementById('admin-password').value;

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Password salah');
    }
    document.getElementById('admin-password').value = '';
    await enterDashboard();
  } catch (err) {
    loginError.textContent = err.message;
    loginError.style.display = 'block';
  }
});

document.getElementById('btn-logout').addEventListener('click', async () => {
  await fetch('/api/logout', { method: 'POST' });
  loginScreen.style.display = 'grid';
  adminDashboard.style.display = 'none';
});

async function enterDashboard() {
  loginScreen.style.display = 'none';
  adminDashboard.style.display = 'block';
  await loadProjects();
}

// ---------- Data Load & Save ----------
async function loadProjects() {
  const res = await fetch('data/projects.json?t=' + Date.now());
  const data = await res.json();
  state = { projects: data.projects || [] };
  activeProjectIdx = state.projects.length ? 0 : -1;
  activeRoomIdx = -1;
  renderAll();
}

async function saveAllToServer() {
  try {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Gagal menyimpan data');
    showToast(data.message || 'Semua projek berhasil disimpan!');
  } catch (err) {
    showToast('Error: ' + err.message);
  }
}

async function uploadFile(file, projectSlug) {
  const form = new FormData();
  form.append('file', file);
  form.append('slug', projectSlug || 'general');

  const res = await fetch('/api/upload', {
    method: 'POST',
    body: form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Upload gagal');
  return data.path;
}

// ---------- Rendering ----------
function renderAll() {
  renderProjectList();
  renderProjectForm();
  renderRoomsList();
  renderRoomEditor();
}

function renderProjectList() {
  const listEl = document.getElementById('admin-project-list');
  if (!state.projects.length) {
    listEl.innerHTML = `<p style="color:var(--text-secondary); font-size:0.85rem;">Belum ada projek. Klik "+ Projek" untuk membuat.</p>`;
    return;
  }
  listEl.innerHTML = state.projects
    .map(
      (p, idx) => `
      <div class="project-list-item ${idx === activeProjectIdx ? 'active' : ''}" data-idx="${idx}">
        <div style="font-weight:700; font-size:0.92rem;">${p.name || 'Tanpa Nama'}</div>
        <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:3px;">
          /p/${p.slug || p.id} • ${(p.rooms || []).length} ruangan
        </div>
      </div>`
    )
    .join('');

  listEl.querySelectorAll('.project-list-item').forEach((el) => {
    el.addEventListener('click', () => {
      activeProjectIdx = Number(el.dataset.idx);
      activeRoomIdx = -1;
      renderAll();
    });
  });
}

function renderProjectForm() {
  const proj = getActiveProject();
  const editorArea = document.getElementById('admin-editor-area');
  if (!proj) {
    editorArea.style.display = 'none';
    return;
  }
  editorArea.style.display = 'flex';

  document.getElementById('proj-name').value = proj.name || '';
  document.getElementById('proj-slug').value = proj.slug || '';
  document.getElementById('proj-subtitle').value = proj.subtitle || '';
  document.getElementById('proj-location').value = proj.location || '';
  document.getElementById('proj-price').value = proj.price || '';
  document.getElementById('proj-desc').value = proj.description || '';
  document.getElementById('proj-thumb-path').textContent = proj.thumbnail || 'Belum ada';
  document.getElementById('proj-floorplan-path').textContent = proj.floorplan || 'Belum ada';
  document.getElementById('btn-preview-project').href = `viewer.html?p=${encodeURIComponent(proj.slug || proj.id)}`;

  const defaultSelect = document.getElementById('proj-default-room');
  defaultSelect.innerHTML = (proj.rooms || [])
    .map(
      (r) => `<option value="${r.id}" ${r.id === proj.defaultRoomId ? 'selected' : ''}>${r.name}</option>`
    )
    .join('');
}

function renderRoomsList() {
  const proj = getActiveProject();
  const listEl = document.getElementById('admin-rooms-list');
  if (!proj) return;
  const rooms = proj.rooms || [];

  if (!rooms.length) {
    listEl.innerHTML = `<p style="color:var(--text-secondary); font-size:0.85rem;">Belum ada ruangan. Klik "+ Tambah Ruangan".</p>`;
    return;
  }

  listEl.innerHTML = rooms
    .map(
      (r, idx) => `
      <div class="room-list-row ${idx === activeRoomIdx ? 'active' : ''}">
        <div style="display:flex; align-items:center; gap:10px;">
          <span class="cat-dot ${r.category || 'interior'}"></span>
          <div>
            <div style="font-weight:600; font-size:0.9rem;">${r.name}</div>
            <div style="font-size:0.74rem; color:var(--text-secondary);">
              ${r.category === 'exterior' ? 'Exterior' : 'Interior'} • ${(r.hotspots || []).length} panah hotspot
            </div>
          </div>
        </div>
        <div style="display:flex; gap:6px;">
          <button class="btn btn-sm btn-edit-room" data-idx="${idx}">Edit &amp; Posisi</button>
          <button class="btn btn-danger btn-sm btn-del-room" data-idx="${idx}">Hapus</button>
        </div>
      </div>`
    )
    .join('');

  listEl.querySelectorAll('.btn-edit-room').forEach((btn) => {
    btn.addEventListener('click', () => {
      activeRoomIdx = Number(btn.dataset.idx);
      renderRoomsList();
      renderRoomEditor();
    });
  });

  listEl.querySelectorAll('.btn-del-room').forEach((btn) => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.dataset.idx);
      proj.rooms.splice(idx, 1);
      if (activeRoomIdx === idx) activeRoomIdx = -1;
      else if (activeRoomIdx > idx) activeRoomIdx--;
      renderAll();
    });
  });
}

function renderEditorFloorplanPins() {
  const proj = getActiveProject();
  const room = getActiveRoom();
  const pinsEl = document.getElementById('editor-floorplan-pins');
  const imgEl = document.getElementById('editor-floorplan-img');
  if (!proj || !room) return;

  imgEl.src = resolveAssetUrl(proj.floorplan || 'assets/demo/denah-anggrek.svg');
  pinsEl.innerHTML = '';

  (proj.rooms || []).forEach((r) => {
    if (typeof r.pinX !== 'number' || typeof r.pinY !== 'number') return;
    const pin = document.createElement('div');
    pin.className = `floorplan-pin ${r.category || 'interior'} ${r.id === room.id ? 'active' : ''}`;
    pin.style.left = `${r.pinX}%`;
    pin.style.top = `${r.pinY}%`;
    pin.innerHTML = `<span class="floorplan-pin-tooltip">${r.name}</span>`;
    pinsEl.appendChild(pin);
  });

  document.getElementById('pin-coords-label').textContent =
    typeof room.pinX === 'number' ? `X: ${room.pinX.toFixed(1)}%, Y: ${room.pinY.toFixed(1)}%` : 'Belum ditentukan (klik denah)';
}

function renderHotspotsList() {
  const proj = getActiveProject();
  const room = getActiveRoom();
  const listEl = document.getElementById('editor-hotspots-list');
  if (!proj || !room) return;

  const hotspots = room.hotspots || [];
  if (!hotspots.length) {
    listEl.innerHTML = `<p style="font-size:0.78rem; color:var(--text-secondary);">Belum ada panah pindah ruangan. Pilih target di atas lalu klik pada foto 360°.</p>`;
    return;
  }

  listEl.innerHTML = hotspots
    .map((hs, idx) => {
      const target = (proj.rooms || []).find((r) => r.id === hs.targetRoomId);
      return `
        <div class="room-list-row" style="padding:6px 10px; margin-bottom:0;">
          <span style="font-size:0.8rem;">➡️ <strong>${hs.label || (target ? target.name : hs.targetRoomId)}</strong> (${hs.yaw}°, ${hs.pitch}°)</span>
          <button class="btn btn-danger btn-sm btn-del-hs" data-idx="${idx}" style="padding:3px 8px;">Hapus</button>
        </div>`;
    })
    .join('');

  listEl.querySelectorAll('.btn-del-hs').forEach((btn) => {
    btn.addEventListener('click', () => {
      room.hotspots.splice(Number(btn.dataset.idx), 1);
      if (editorViewer) editorViewer.setHotspots(room.hotspots);
      renderHotspotsList();
      renderRoomsList();
    });
  });
}

async function renderRoomEditor() {
  const proj = getActiveProject();
  const room = getActiveRoom();
  const panel = document.getElementById('room-editor-panel');

  if (!proj || !room) {
    panel.style.display = 'none';
    return;
  }
  panel.style.display = 'block';

  document.getElementById('room-name').value = room.name || '';
  document.getElementById('room-category').value = room.category || 'interior';
  document.getElementById('room-pano-path').textContent = room.panorama || 'Belum ada foto 360°';
  document.getElementById('room-north').value = room.northOffset || 0;
  document.getElementById('north-val').textContent = room.northOffset || 0;

  // Target room dropdown for hotspot placement
  const targetSelect = document.getElementById('hotspot-target-select');
  const otherRooms = (proj.rooms || []).filter((r) => r.id !== room.id);
  targetSelect.innerHTML = otherRooms.length
    ? otherRooms.map((r) => `<option value="${r.id}">Tujuan: ${r.name}</option>`).join('')
    : `<option value="">Tambah ruangan lain dulu</option>`;

  renderEditorFloorplanPins();
  renderHotspotsList();

  // Initialize or update 360 editor viewer
  if (!editorViewer) {
    editorViewer = new PanoViewer(
      document.getElementById('editor-pano-canvas'),
      document.getElementById('editor-hotspots-layer'),
      {
        onPickPoint: ({ yaw, pitch }) => {
          const curRoom = getActiveRoom();
          const curProj = getActiveProject();
          if (!curRoom || !curProj) return;
          const targetId = document.getElementById('hotspot-target-select').value;
          if (!targetId) {
            showToast('Pilih ruangan tujuan terlebih dahulu.');
            return;
          }
          const targetRoom = curProj.rooms.find((r) => r.id === targetId);
          const customLabel = document.getElementById('hotspot-label-input').value.trim();
          const label = customLabel || `Ke ${targetRoom ? targetRoom.name : targetId}`;

          curRoom.hotspots = curRoom.hotspots || [];
          curRoom.hotspots.push({
            id: 'hs-' + Date.now(),
            yaw,
            pitch,
            targetRoomId: targetId,
            label,
          });
          document.getElementById('hotspot-label-input').value = '';
          editorViewer.setHotspots(curRoom.hotspots);
          renderHotspotsList();
          renderRoomsList();
          showToast(`Panah ke "${label}" ditambahkan!`);
        },
      }
    );
  }

  editorViewer.resize();
  if (room.panorama) {
    try {
      await editorViewer.loadPanorama(resolveAssetUrl(room.panorama), room.initialYaw || 0, room.hotspots || []);
    } catch {
      showToast('Gagal memuat preview 360°.');
    }
  }
}

// ---------- Form & Editor Event Bindings ----------
function bindEvents() {
  document.getElementById('btn-save-all').addEventListener('click', saveAllToServer);

  document.getElementById('btn-export-json').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'projects.json';
    a.click();
    URL.revokeObjectURL(url);
  });

  document.getElementById('btn-new-project').addEventListener('click', () => {
    const num = state.projects.length + 1;
    const slug = `projek-rumah-${num}`;
    state.projects.push({
      id: slug,
      slug,
      name: `Projek Rumah ${num}`,
      subtitle: 'Tipe Baru • Modern Residence',
      location: 'Lokasi Projek',
      price: 'Hubungi Marketing',
      description: 'Deskripsi singkat projek rumah.',
      thumbnail: 'assets/demo/exterior-fasad.png',
      floorplan: 'assets/demo/denah-anggrek.svg',
      defaultRoomId: '',
      rooms: [],
    });
    activeProjectIdx = state.projects.length - 1;
    activeRoomIdx = -1;
    renderAll();
  });

  document.getElementById('btn-delete-project').addEventListener('click', () => {
    const proj = getActiveProject();
    if (!proj) return;
    if (!confirm(`Hapus projek "${proj.name}"?`)) return;
    state.projects.splice(activeProjectIdx, 1);
    activeProjectIdx = state.projects.length ? 0 : -1;
    activeRoomIdx = -1;
    renderAll();
  });

  // Project fields live sync
  const bindProjField = (id, key, transform) => {
    document.getElementById(id).addEventListener('input', (e) => {
      const proj = getActiveProject();
      if (!proj) return;
      proj[key] = transform ? transform(e.target.value) : e.target.value;
      if (key === 'name' || key === 'slug') {
        renderProjectList();
        document.getElementById('btn-preview-project').href = `viewer.html?p=${encodeURIComponent(proj.slug || proj.id)}`;
      }
    });
  };

  bindProjField('proj-name', 'name');
  bindProjField('proj-slug', 'slug', slugify);
  bindProjField('proj-subtitle', 'subtitle');
  bindProjField('proj-location', 'location');
  bindProjField('proj-price', 'price');
  bindProjField('proj-desc', 'description');
  bindProjField('proj-default-room', 'defaultRoomId');

  // Upload Thumbnail
  document.getElementById('upload-thumbnail').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    const proj = getActiveProject();
    if (!file || !proj) return;
    try {
      showToast('Mengupload thumbnail...');
      const path = await uploadFile(file, proj.slug);
      proj.thumbnail = path;
      document.getElementById('proj-thumb-path').textContent = path;
      showToast('Thumbnail berhasil diupload!');
    } catch (err) {
      showToast('Upload gagal: ' + err.message);
    }
  });

  // Upload Floorplan
  document.getElementById('upload-floorplan').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    const proj = getActiveProject();
    if (!file || !proj) return;
    try {
      showToast('Mengupload denah...');
      const path = await uploadFile(file, proj.slug);
      proj.floorplan = path;
      document.getElementById('proj-floorplan-path').textContent = path;
      renderEditorFloorplanPins();
      showToast('Denah berhasil diupload!');
    } catch (err) {
      showToast('Upload gagal: ' + err.message);
    }
  });

  // Add Room
  document.getElementById('btn-add-room').addEventListener('click', () => {
    const proj = getActiveProject();
    if (!proj) return;
    proj.rooms = proj.rooms || [];
    const idx = proj.rooms.length + 1;
    const roomId = `ruangan-${idx}-${Date.now().toString().slice(-4)}`;
    proj.rooms.push({
      id: roomId,
      name: `Ruangan ${idx}`,
      category: 'interior',
      panorama: 'assets/demo/living-room.png',
      pinX: 50,
      pinY: 50,
      initialYaw: 0,
      northOffset: 0,
      hotspots: [],
    });
    if (!proj.defaultRoomId) proj.defaultRoomId = roomId;
    activeRoomIdx = proj.rooms.length - 1;
    renderAll();
  });

  // Room fields live sync
  document.getElementById('room-name').addEventListener('input', (e) => {
    const room = getActiveRoom();
    if (!room) return;
    room.name = e.target.value;
    renderRoomsList();
    renderProjectForm();
    renderEditorFloorplanPins();
  });

  document.getElementById('room-category').addEventListener('change', (e) => {
    const room = getActiveRoom();
    if (!room) return;
    room.category = e.target.value;
    renderRoomsList();
    renderEditorFloorplanPins();
  });

  document.getElementById('room-north').addEventListener('input', (e) => {
    const room = getActiveRoom();
    if (!room) return;
    room.northOffset = Number(e.target.value);
    document.getElementById('north-val').textContent = e.target.value;
  });

  // Upload Room 360 Panorama
  document.getElementById('upload-room-pano').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    const proj = getActiveProject();
    const room = getActiveRoom();
    if (!file || !proj || !room) return;
    try {
      showToast('Mengupload foto 360°...');
      const path = await uploadFile(file, proj.slug);
      room.panorama = path;
      document.getElementById('room-pano-path').textContent = path;
      await renderRoomEditor();
      showToast('Foto 360° berhasil diupload!');
    } catch (err) {
      showToast('Upload gagal: ' + err.message);
    }
  });

  // Click on Floorplan to place pin
  document.getElementById('editor-floorplan-box').addEventListener('click', (e) => {
    const room = getActiveRoom();
    if (!room) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const xPct = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
    const yPct = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100));
    room.pinX = Number(xPct.toFixed(1));
    room.pinY = Number(yPct.toFixed(1));
    renderEditorFloorplanPins();
    showToast(`Titik "${room.name}" dipindahkan ke (${room.pinX}%, ${room.pinY}%)`);
  });
}

bindEvents();
checkAuth();
