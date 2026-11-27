import { PanoViewer } from './pano-viewer.js';

const projectNameEl = document.getElementById('project-name');
const roomSubtitleEl = document.getElementById('room-subtitle');
const floorplanImg = document.getElementById('floorplan-img');
const floorplanPinsEl = document.getElementById('floorplan-pins');
const radarConeEl = document.getElementById('radar-cone');
const radarSvgEl = document.getElementById('radar-svg');
const roomStripEl = document.getElementById('room-strip');
const minimapWidget = document.getElementById('minimap-widget');
const vrHud = document.getElementById('vr-overlay-hud');
const toastEl = document.getElementById('toast');

let currentProject = null;
let currentRoom = null;
let viewer = null;

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  setTimeout(() => toastEl.classList.remove('show'), 2600);
}

function getRequestedSlug() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('p')) return params.get('p');
  const match = window.location.pathname.match(/\/p\/([^/]+)/);
  if (match && match[1]) return decodeURIComponent(match[1]);
  return null;
}

function resolveAssetUrl(path) {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
    return path;
  }
  return path.replace(/^\/+/, '');
}

function renderFloorplanPins() {
  if (!currentProject) return;
  const rooms = currentProject.rooms || [];
  floorplanPinsEl.innerHTML = '';

  rooms.forEach((room) => {
    if (typeof room.pinX !== 'number' || typeof room.pinY !== 'number') return;
    const pin = document.createElement('button');
    const isActive = currentRoom && currentRoom.id === room.id;
    pin.className = `floorplan-pin ${room.category || 'interior'} ${isActive ? 'active' : ''}`;
    pin.style.left = `${room.pinX}%`;
    pin.style.top = `${room.pinY}%`;
    pin.title = room.name;
    pin.innerHTML = `<span class="floorplan-pin-tooltip">${room.name}</span>`;
    pin.addEventListener('click', () => selectRoom(room.id));
    floorplanPinsEl.appendChild(pin);
  });

  if (currentRoom && typeof currentRoom.pinX === 'number' && typeof currentRoom.pinY === 'number') {
    radarConeEl.style.display = 'block';
    radarConeEl.style.left = `${currentRoom.pinX}%`;
    radarConeEl.style.top = `${currentRoom.pinY}%`;
  } else {
    radarConeEl.style.display = 'none';
  }
}

function renderRoomStrip() {
  if (!currentProject) return;
  const rooms = currentProject.rooms || [];
  roomStripEl.innerHTML = '';

  rooms.forEach((room) => {
    const btn = document.createElement('button');
    const isActive = currentRoom && currentRoom.id === room.id;
    btn.className = `room-chip ${isActive ? 'active' : ''}`;
    btn.innerHTML = `
      <span class="cat-dot ${room.category || 'interior'}"></span>
      <span>${room.name}</span>
    `;
    btn.addEventListener('click', () => selectRoom(room.id));
    roomStripEl.appendChild(btn);
  });
}

async function selectRoom(roomId) {
  if (!currentProject) return;
  const room = (currentProject.rooms || []).find((r) => r.id === roomId);
  if (!room) return;
  currentRoom = room;

  const catLabel = room.category === 'exterior' ? 'Exterior' : 'Interior';
  roomSubtitleEl.textContent = `${catLabel} • ${room.name}`;
  document.title = `${room.name} — ${currentProject.name}`;

  renderFloorplanPins();
  renderRoomStrip();

  try {
    await viewer.loadPanorama(
      resolveAssetUrl(room.panorama),
      room.initialYaw || 0,
      room.hotspots || []
    );
  } catch (err) {
    showToast('Gagal memuat foto 360° ruangan ini.');
  }
}

function bindControls() {
  const btnAuto = document.getElementById('btn-autorotate');
  const btnGyro = document.getElementById('btn-gyro');
  const btnVr = document.getElementById('btn-vr');
  const btnExitVr = document.getElementById('btn-exit-vr');
  const btnShare = document.getElementById('btn-share');
  const btnFullscreen = document.getElementById('btn-fullscreen');
  const btnExpand = document.getElementById('btn-minimap-expand');
  const btnToggle = document.getElementById('btn-minimap-toggle');

  btnAuto.addEventListener('click', () => {
    const next = !viewer.autoRotate;
    viewer.setAutoRotate(next);
    btnAuto.classList.toggle('active', next);
  });

  btnGyro.addEventListener('click', async () => {
    const next = !viewer.gyroEnabled;
    try {
      await viewer.setGyroEnabled(next);
      btnGyro.classList.toggle('active', next);
      showToast(next ? 'Sensor Gyroscope aktif' : 'Sensor Gyroscope dimatikan');
    } catch (err) {
      showToast(err.message || 'Perangkat tidak mendukung Gyroscope');
    }
  });

  const toggleVr = (enable) => {
    viewer.setStereoMode(enable);
    vrHud.classList.toggle('active', enable);
    document.getElementById('viewer-topbar').style.display = enable ? 'none' : 'flex';
    document.getElementById('viewer-bottombar').style.display = enable ? 'none' : 'flex';
    minimapWidget.style.display = enable ? 'none' : 'block';
    if (enable && document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  };

  btnVr.addEventListener('click', () => toggleVr(true));
  btnExitVr.addEventListener('click', () => toggleVr(false));

  btnShare.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      showToast('Link tur 360° berhasil disalin!');
    } catch {
      showToast(window.location.href);
    }
  });

  btnFullscreen.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  });

  btnExpand.addEventListener('click', () => {
    minimapWidget.classList.toggle('expanded');
  });

  btnToggle.addEventListener('click', () => {
    const collapsed = minimapWidget.classList.toggle('collapsed');
    btnToggle.textContent = collapsed ? '+' : '−';
  });
}

async function init() {
  const container = document.getElementById('pano-canvas-container');
  const hotspotsLayer = document.getElementById('hotspots-layer');

  viewer = new PanoViewer(container, hotspotsLayer, {
    onHotspotClick: (hs) => {
      if (hs.targetRoomId) {
        selectRoom(hs.targetRoomId);
      }
    },
    onYawChange: (yawDeg) => {
      if (!currentRoom) return;
      const offset = Number(currentRoom.northOffset || 0);
      const angle = yawDeg + offset;
      radarSvgEl.style.transform = `rotate(${angle}deg)`;
    },
  });

  bindControls();

  try {
    const res = await fetch('data/projects.json?t=' + Date.now());
    const data = await res.json();
    const projects = data.projects || [];
    const slug = getRequestedSlug();

    currentProject =
      projects.find((p) => p.slug === slug || p.id === slug) || projects[0];

    if (!currentProject) {
      projectNameEl.textContent = 'Projek tidak ditemukan';
      return;
    }

    projectNameEl.textContent = currentProject.name;
    if (currentProject.floorplan) {
      floorplanImg.src = resolveAssetUrl(currentProject.floorplan);
    } else {
      minimapWidget.style.display = 'none';
    }

    const startRoomId =
      currentProject.defaultRoomId ||
      (currentProject.rooms && currentProject.rooms[0] && currentProject.rooms[0].id);

    if (startRoomId) {
      await selectRoom(startRoomId);
    }
  } catch (err) {
    projectNameEl.textContent = 'Gagal memuat data projek';
    showToast(err.message);
  }
}

init();
