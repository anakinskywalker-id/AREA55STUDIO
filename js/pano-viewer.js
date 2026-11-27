import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';

/**
 * Reusable Three.js 360° Panorama + VR Stereo + Gyroscope + Hotspot Viewer
 */
export class PanoViewer {
  constructor(container, hotspotsLayer, options = {}) {
    this.container = container;
    this.hotspotsLayer = hotspotsLayer;
    this.options = options;

    this.lon = 0; // yaw in degrees
    this.lat = 0; // pitch in degrees
    this.fov = 75;
    this.autoRotate = false;
    this.stereoMode = false;
    this.gyroEnabled = false;
    this.hotspots = [];
    this.hotspotElements = [];

    this.isPointerDown = false;
    this.pointerDownX = 0;
    this.pointerDownY = 0;
    this.onPointerDownLon = 0;
    this.onPointerDownLat = 0;
    this.movedDistance = 0;

    this._initThree();
    this._bindEvents();
    this._animate();
  }

  _initThree() {
    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(this.fov, width / height, 1, 1100);
    this.cameraLeft = new THREE.PerspectiveCamera(this.fov, (width / 2) / height, 1, 1100);
    this.cameraRight = new THREE.PerspectiveCamera(this.fov, (width / 2) / height, 1, 1100);

    const geometry = new THREE.SphereGeometry(500, 60, 40);
    geometry.scale(-1, 1, 1);

    this.material = new THREE.MeshBasicMaterial({ color: 0xffffff });
    this.sphere = new THREE.Mesh(geometry, this.material);
    this.scene.add(this.sphere);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(width, height);
    this.container.innerHTML = '';
    this.container.appendChild(this.renderer.domElement);

    this.textureLoader = new THREE.TextureLoader();
    this.textureLoader.setCrossOrigin('anonymous');
  }

  _bindEvents() {
    const el = this.renderer.domElement;

    this._onPointerDown = (e) => {
      this.isPointerDown = true;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      this.pointerDownX = clientX;
      this.pointerDownY = clientY;
      this.onPointerDownLon = this.lon;
      this.onPointerDownLat = this.lat;
      this.movedDistance = 0;
    };

    this._onPointerMove = (e) => {
      if (!this.isPointerDown) return;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const dx = clientX - this.pointerDownX;
      const dy = clientY - this.pointerDownY;
      this.movedDistance = Math.hypot(dx, dy);
      this.lon = (this.pointerDownX - clientX) * 0.16 + this.onPointerDownLon;
      this.lat = (clientY - this.pointerDownY) * 0.16 + this.onPointerDownLat;
      this.lat = Math.max(-85, Math.min(85, this.lat));
    };

    this._onPointerUp = (e) => {
      if (!this.isPointerDown) return;
      this.isPointerDown = false;

      // Treat as click/tap if pointer didn't drag
      if (this.movedDistance < 6 && typeof this.options.onPickPoint === 'function') {
        const rect = el.getBoundingClientRect();
        const clientX = e.changedTouches ? e.changedTouches[0].clientX : e.clientX;
        const clientY = e.changedTouches ? e.changedTouches[0].clientY : e.clientY;
        const ndcX = ((clientX - rect.left) / rect.width) * 2 - 1;
        const ndcY = -((clientY - rect.top) / rect.height) * 2 + 1;

        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(new THREE.Vector2(ndcX, ndcY), this.camera);
        const intersects = raycaster.intersectObject(this.sphere);
        if (intersects.length > 0) {
          const pt = intersects[0].point.clone().normalize();
          const pitch = THREE.MathUtils.radToDeg(Math.asin(Math.max(-1, Math.min(1, pt.y))));
          const yaw = THREE.MathUtils.radToDeg(Math.atan2(pt.z, pt.x));
          this.options.onPickPoint({
            yaw: Number(yaw.toFixed(1)),
            pitch: Number(pitch.toFixed(1)),
          });
        }
      }
    };

    this._onWheel = (e) => {
      e.preventDefault();
      this.fov = Math.max(35, Math.min(95, this.fov + e.deltaY * 0.04));
      this.camera.fov = this.fov;
      this.camera.updateProjectionMatrix();
    };

    this._onResize = () => this.resize();

    this._onDeviceOrientation = (event) => {
      if (!this.gyroEnabled || event.alpha === null) return;
      // Map alpha/beta smoothly to lon/lat
      const alpha = event.alpha || 0;
      const beta = event.beta || 90;
      this.lon = -alpha;
      this.lat = Math.max(-85, Math.min(85, beta - 90));
    };

    el.addEventListener('mousedown', this._onPointerDown);
    window.addEventListener('mousemove', this._onPointerMove);
    window.addEventListener('mouseup', this._onPointerUp);
    el.addEventListener('touchstart', this._onPointerDown, { passive: true });
    window.addEventListener('touchmove', this._onPointerMove, { passive: true });
    window.addEventListener('touchend', this._onPointerUp);
    el.addEventListener('wheel', this._onWheel, { passive: false });
    window.addEventListener('resize', this._onResize);
    window.addEventListener('deviceorientation', this._onDeviceOrientation);
  }

  resize() {
    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  loadPanorama(imageUrl, initialYaw = 0, hotspots = []) {
    this.lon = initialYaw;
    this.lat = 0;
    this.setHotspots(hotspots);

    return new Promise((resolve, reject) => {
      this.textureLoader.load(
        imageUrl,
        (texture) => {
          texture.colorSpace = THREE.SRGBColorSpace;
          if (this.material.map) this.material.map.dispose();
          this.material.map = texture;
          this.material.needsUpdate = true;
          resolve();
        },
        undefined,
        (err) => reject(err)
      );
    });
  }

  setHotspots(hotspots = []) {
    this.hotspots = hotspots;
    if (!this.hotspotsLayer) return;
    this.hotspotsLayer.innerHTML = '';
    this.hotspotElements = hotspots.map((hs) => {
      const el = document.createElement('div');
      el.className = 'hotspot-marker';
      el.innerHTML = `
        <div class="hotspot-dot" title="${hs.label || ''}">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M12 19V5M5 12l7-7 7 7"/>
          </svg>
        </div>
        <span class="hotspot-label">${hs.label || 'Pindah Ruangan'}</span>
      `;
      el.addEventListener('click', (ev) => {
        ev.stopPropagation();
        if (typeof this.options.onHotspotClick === 'function') {
          this.options.onHotspotClick(hs);
        }
      });
      this.hotspotsLayer.appendChild(el);
      return { data: hs, el };
    });
  }

  setAutoRotate(enabled) {
    this.autoRotate = Boolean(enabled);
  }

  setStereoMode(enabled) {
    this.stereoMode = Boolean(enabled);
    this.renderer.setScissorTest(this.stereoMode);
    if (!this.stereoMode) {
      const width = this.container.clientWidth || window.innerWidth;
      const height = this.container.clientHeight || window.innerHeight;
      this.renderer.setViewport(0, 0, width, height);
    }
  }

  async setGyroEnabled(enabled) {
    if (enabled && typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
      const perm = await DeviceOrientationEvent.requestPermission();
      if (perm !== 'granted') {
        throw new Error('Izin sensor gyroscope ditolak.');
      }
    }
    this.gyroEnabled = Boolean(enabled);
  }

  _yawPitchToVector(yawDeg, pitchDeg, radius = 480) {
    const phi = THREE.MathUtils.degToRad(90 - pitchDeg);
    const theta = THREE.MathUtils.degToRad(yawDeg);
    return new THREE.Vector3(
      radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta)
    );
  }

  _updateHotspots() {
    if (!this.hotspotsLayer || this.stereoMode) {
      if (this.hotspotsLayer) this.hotspotsLayer.style.display = this.stereoMode ? 'none' : 'block';
      return;
    }
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    const camDir = new THREE.Vector3();
    this.camera.getWorldDirection(camDir);

    for (const item of this.hotspotElements) {
      const pos = this._yawPitchToVector(item.data.yaw, item.data.pitch);
      const dirToPt = pos.clone().normalize();
      const dot = camDir.dot(dirToPt);

      if (dot <= 0.1) {
        item.el.style.display = 'none';
        continue;
      }

      const projected = pos.clone().project(this.camera);
      const x = (projected.x * 0.5 + 0.5) * width;
      const y = (-projected.y * 0.5 + 0.5) * height;
      item.el.style.display = 'flex';
      item.el.style.left = `${x}px`;
      item.el.style.top = `${y}px`;
    }
  }

  _animate() {
    this._rafId = requestAnimationFrame(() => this._animate());

    if (this.autoRotate && !this.isPointerDown && !this.gyroEnabled) {
      this.lon += 0.08;
    }

    const target = this._yawPitchToVector(this.lon, this.lat, 500);
    this.camera.position.set(0, 0, 0);
    this.camera.lookAt(target);

    if (typeof this.options.onYawChange === 'function') {
      const normalizedYaw = ((this.lon % 360) + 360) % 360;
      this.options.onYawChange(normalizedYaw);
    }

    if (this.stereoMode) {
      const width = this.container.clientWidth || window.innerWidth;
      const height = this.container.clientHeight || window.innerHeight;
      const halfW = Math.floor(width / 2);

      // Left eye
      this.cameraLeft.fov = this.fov;
      this.cameraLeft.aspect = halfW / height;
      this.cameraLeft.updateProjectionMatrix();
      this.cameraLeft.position.set(-0.032, 0, 0);
      this.cameraLeft.lookAt(target);
      this.renderer.setViewport(0, 0, halfW, height);
      this.renderer.setScissor(0, 0, halfW, height);
      this.renderer.render(this.scene, this.cameraLeft);

      // Right eye
      this.cameraRight.fov = this.fov;
      this.cameraRight.aspect = halfW / height;
      this.cameraRight.updateProjectionMatrix();
      this.cameraRight.position.set(0.032, 0, 0);
      this.cameraRight.lookAt(target);
      this.renderer.setViewport(halfW, 0, halfW, height);
      this.renderer.setScissor(halfW, 0, halfW, height);
      this.renderer.render(this.scene, this.cameraRight);
    } else {
      this.renderer.render(this.scene, this.camera);
    }

    this._updateHotspots();
  }

  dispose() {
    cancelAnimationFrame(this._rafId);
    window.removeEventListener('mousemove', this._onPointerMove);
    window.removeEventListener('mouseup', this._onPointerUp);
    window.removeEventListener('touchmove', this._onPointerMove);
    window.removeEventListener('touchend', this._onPointerUp);
    window.removeEventListener('resize', this._onResize);
    window.removeEventListener('deviceorientation', this._onDeviceOrientation);
    this.renderer.dispose();
  }
}
