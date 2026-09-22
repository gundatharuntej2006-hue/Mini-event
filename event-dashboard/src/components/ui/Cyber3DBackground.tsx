import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

/**
 * Checks whether WebGL is available in the current browser environment.
 */
function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

/**
 * Helper to generate a crisp high-res holographic text billboard texture
 */
function createHoloTextTexture(
  lines: string[],
  accentColor: string = '#22d3ee',
  borderColor?: string,
  hasBrackets: boolean = false
): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d')!;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (borderColor) {
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = 3;
    ctx.strokeRect(16, 16, canvas.width - 32, canvas.height - 32);

    if (hasBrackets) {
      // Corner brackets
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 4;
      const bl = 24;
      // Top-left
      ctx.beginPath();
      ctx.moveTo(16, 16 + bl);
      ctx.lineTo(16, 16);
      ctx.lineTo(16 + bl, 16);
      ctx.stroke();
      // Top-right
      ctx.beginPath();
      ctx.moveTo(canvas.width - 16 - bl, 16);
      ctx.lineTo(canvas.width - 16, 16);
      ctx.lineTo(canvas.width - 16, 16 + bl);
      ctx.stroke();
      // Bottom-left
      ctx.beginPath();
      ctx.moveTo(16, canvas.height - 16 - bl);
      ctx.lineTo(16, canvas.height - 16);
      ctx.lineTo(16 + bl, canvas.height - 16);
      ctx.stroke();
      // Bottom-right
      ctx.beginPath();
      ctx.moveTo(canvas.width - 16 - bl, canvas.height - 16);
      ctx.lineTo(canvas.width - 16, canvas.height - 16);
      ctx.lineTo(canvas.width - 16, canvas.height - 16 - bl);
      ctx.stroke();
    }
  }

  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = '900 36px Orbitron, sans-serif';
  ctx.fillStyle = accentColor;
  ctx.shadowColor = accentColor;
  ctx.shadowBlur = 18;

  const lineHeight = 46;
  const startY = canvas.height / 2 - ((lines.length - 1) * lineHeight) / 2;

  lines.forEach((line, index) => {
    ctx.fillText(line, canvas.width / 2, startY + index * lineHeight);
  });

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

/**
 * Helper to generate floating BMSIT holographic logo badge texture
 */
function createBmsitBadgeTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 384;
  canvas.height = 128;
  const ctx = canvas.getContext('2d')!;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Background subtle glow pill
  ctx.fillStyle = 'rgba(6, 182, 212, 0.15)';
  ctx.strokeStyle = '#22d3ee';
  ctx.lineWidth = 2.5;

  const rx = 24, ry = 24, rw = canvas.width - 48, rh = canvas.height - 48;
  ctx.beginPath();
  ctx.roundRect(rx, ry, rw, rh, 16);
  ctx.fill();
  ctx.stroke();

  // BMSIT glowing text
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = '900 52px Orbitron, sans-serif';
  ctx.fillStyle = '#ffffff';
  ctx.shadowColor = '#22d3ee';
  ctx.shadowBlur = 24;
  ctx.fillText('BMSIT', canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

/**
 * Cyber3DBackground
 * 
 * Reusable, hardware-accelerated 3D environment that matches the futuristic control room:
 * - Immersive 3D sci-fi control room with illuminated columns, overhead trusses, and reflective glossy floor
 * - Prominent 3D holographic Earth globe positioned in the upper center hero
 * - Continental cyan circuitry/dot-matrix texture
 * - Dual tilted, revolving glowing orbital rings with telemetry nodes
 * - Floating "BMSIT" holographic brand badge centered on the globe
 * - Flanking holographic panes: "COMPETE STRATEGIZE DOMINATE" & "IDEAS PEOPLE IMPACT"
 * - Far-right futuristic server terminal: "MORE THAN A HACKATHON"
 * - Responsive mouse parallax camera damping
 * - Tab inactivity rendering pause (0% GPU when backgrounded)
 * - prefers-reduced-motion compliance
 * - Pointer-events-none non-blocking interaction
 */
export function Cyber3DBackground() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasWebGL, setHasWebGL] = useState<boolean>(true);

  useEffect(() => {
    if (!isWebGLAvailable()) {
      setHasWebGL(false);
      return;
    }

    const container = containerRef.current;
    if (!container) return;

    // Check motion preferences
    const prefersReducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    let prefersReducedMotion = prefersReducedMotionQuery.matches;

    const handleMotionChange = (e: MediaQueryListEvent) => {
      prefersReducedMotion = e.matches;
    };
    prefersReducedMotionQuery.addEventListener('change', handleMotionChange);

    // Arrays to collect WebGL resources for disposal on unmount
    const geometriesToDispose: THREE.BufferGeometry[] = [];
    const materialsToDispose: THREE.Material[] = [];
    const texturesToDispose: THREE.Texture[] = [];

    // 1. Scene, Camera & Fog
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030712, 0.022);

    const camera = new THREE.PerspectiveCamera(
      52,
      window.innerWidth / window.innerHeight,
      0.1,
      120
    );
    camera.position.set(0, 1.2, 13.5);

    // 2. Renderer
    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      });
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
      renderer.setClearColor(0x030712, 0);
      container.appendChild(renderer.domElement);
    } catch (err) {
      console.warn('WebGL initialization failed, falling back to CSS:', err);
      setHasWebGL(false);
      return;
    }

    // 3. Ambient & Cyber Lighting
    const ambientLight = new THREE.AmbientLight(0x061124, 3.0);
    scene.add(ambientLight);

    // Key cyan light shining on the globe
    const cyanLight = new THREE.PointLight(0x00f0ff, 4.0, 30);
    cyanLight.position.set(-2, 4, 6);
    scene.add(cyanLight);

    // Violet accent light for side reflections
    const violetLight = new THREE.PointLight(0xa855f7, 3.5, 30);
    violetLight.position.set(6, 2, 6);
    scene.add(violetLight);

    // 4. Control Room Hangar Backdrop Plane
    const textureLoader = new THREE.TextureLoader();
    const bgTexture = textureLoader.load(
      '/cyber-control-room.jpg',
      () => {
        bgTexture.colorSpace = THREE.SRGBColorSpace;
      },
      undefined,
      (err) => {
        console.warn('Could not load control room backdrop texture:', err);
      }
    );
    texturesToDispose.push(bgTexture);

    const bgGeometry = new THREE.PlaneGeometry(36, 20.25);
    geometriesToDispose.push(bgGeometry);

    const bgMaterial = new THREE.MeshBasicMaterial({
      map: bgTexture,
      transparent: true,
      opacity: 0.85,
    });
    materialsToDispose.push(bgMaterial);

    const bgMesh = new THREE.Mesh(bgGeometry, bgMaterial);
    bgMesh.position.set(0, 1.5, -9);
    scene.add(bgMesh);

    // 5. Reflective Sci-Fi Grid Floor Plane
    const floorGeometry = new THREE.PlaneGeometry(50, 40, 30, 24);
    geometriesToDispose.push(floorGeometry);

    const floorMaterial = new THREE.MeshBasicMaterial({
      color: 0x06b6d4,
      wireframe: true,
      transparent: true,
      opacity: 0.08,
    });
    materialsToDispose.push(floorMaterial);

    const floorMesh = new THREE.Mesh(floorGeometry, floorMaterial);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.set(0, -5.2, -2);
    scene.add(floorMesh);

    // 6. Central Holographic Earth Globe
    // Positioned in upper center hero area
    const globeGroup = new THREE.Group();
    globeGroup.position.set(1.6, 2.6, 0.5);
    scene.add(globeGroup);

    // 6a. Earth Continent Texture
    const earthTexture = textureLoader.load(
      '/earth-hologram.jpg',
      () => {
        earthTexture.colorSpace = THREE.SRGBColorSpace;
      },
      undefined,
      () => {
        console.warn('Could not load earth hologram texture, using wireframe');
      }
    );
    texturesToDispose.push(earthTexture);

    // 6b. Inner Dark Celestial Sphere
    const innerCoreGeo = new THREE.SphereGeometry(2.7, 48, 48);
    geometriesToDispose.push(innerCoreGeo);
    const innerCoreMat = new THREE.MeshBasicMaterial({
      color: 0x030d1e,
      transparent: true,
      opacity: 0.9,
    });
    materialsToDispose.push(innerCoreMat);
    const innerCore = new THREE.Mesh(innerCoreGeo, innerCoreMat);
    globeGroup.add(innerCore);

    // 6c. Continent Holographic Glow Sphere
    const earthGeo = new THREE.SphereGeometry(2.74, 64, 64);
    geometriesToDispose.push(earthGeo);
    const earthMat = new THREE.MeshBasicMaterial({
      map: earthTexture,
      transparent: true,
      opacity: 0.98,
      blending: THREE.AdditiveBlending,
      color: 0x22d3ee,
    });
    materialsToDispose.push(earthMat);
    const earthMesh = new THREE.Mesh(earthGeo, earthMat);
    globeGroup.add(earthMesh);

    // 6d. Longitude & Latitude Wireframe Grid Layer
    const gridGlobeGeo = new THREE.SphereGeometry(2.77, 32, 16);
    geometriesToDispose.push(gridGlobeGeo);
    const gridGlobeMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(gridGlobeMat);
    const gridGlobeMesh = new THREE.Mesh(gridGlobeGeo, gridGlobeMat);
    globeGroup.add(gridGlobeMesh);

    // 6e. Atmospheric Outer Rim Halo (Fresnel)
    const haloGeo = new THREE.SphereGeometry(2.96, 32, 32);
    geometriesToDispose.push(haloGeo);
    const haloMat = new THREE.MeshBasicMaterial({
      color: 0x06b6d4,
      transparent: true,
      opacity: 0.18,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(haloMat);
    const haloMesh = new THREE.Mesh(haloGeo, haloMat);
    globeGroup.add(haloMesh);

    // 6f. Glowing Orbital Rings
    // Ring 1 (Tilted cyan ring with orbiting nodes)
    const ring1Geo = new THREE.TorusGeometry(3.9, 0.024, 16, 120);
    geometriesToDispose.push(ring1Geo);
    const ring1Mat = new THREE.MeshBasicMaterial({
      color: 0x22d3ee,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(ring1Mat);
    const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
    ring1.rotation.x = Math.PI / 3;
    ring1.rotation.y = Math.PI / 6;
    globeGroup.add(ring1);

    // Nodes on Ring 1
    const nodeGeo = new THREE.SphereGeometry(0.08, 12, 12);
    geometriesToDispose.push(nodeGeo);
    const nodeMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(nodeMat);

    const node1 = new THREE.Mesh(nodeGeo, nodeMat);
    const node2 = new THREE.Mesh(nodeGeo, nodeMat);
    ring1.add(node1);
    ring1.add(node2);

    // Ring 2 (Tilted electric violet ring)
    const ring2Geo = new THREE.TorusGeometry(4.7, 0.02, 16, 120);
    geometriesToDispose.push(ring2Geo);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: 0xa855f7,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(ring2Mat);
    const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2.rotation.x = -Math.PI / 4;
    ring2.rotation.y = -Math.PI / 5;
    globeGroup.add(ring2);

    const node3 = new THREE.Mesh(nodeGeo, nodeMat);
    ring2.add(node3);

    // 6g. Floating "BMSIT" Holographic Text Badge
    const bmsitTexture = createBmsitBadgeTexture();
    texturesToDispose.push(bmsitTexture);

    const bmsitGeo = new THREE.PlaneGeometry(2.4, 0.8);
    geometriesToDispose.push(bmsitGeo);
    const bmsitMat = new THREE.MeshBasicMaterial({
      map: bmsitTexture,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(bmsitMat);
    const bmsitMesh = new THREE.Mesh(bmsitGeo, bmsitMat);
    bmsitMesh.position.set(0, 0, 3.1);
    globeGroup.add(bmsitMesh);

    // 7. Flanking 3D Holographic Room Panels
    // Left holographic pane: "COMPETE STRATEGIZE DOMINATE"
    const leftPaneTex = createHoloTextTexture(
      ['COMPETE', 'STRATEGIZE', 'DOMINATE'],
      '#22d3ee',
      'rgba(34, 211, 238, 0.4)',
      true
    );
    texturesToDispose.push(leftPaneTex);

    const leftPaneGeo = new THREE.PlaneGeometry(2.8, 1.4);
    geometriesToDispose.push(leftPaneGeo);
    const leftPaneMat = new THREE.MeshBasicMaterial({
      map: leftPaneTex,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(leftPaneMat);
    const leftPaneMesh = new THREE.Mesh(leftPaneGeo, leftPaneMat);
    leftPaneMesh.position.set(-3.6, 3.4, -1.8);
    leftPaneMesh.rotation.y = 0.18;
    scene.add(leftPaneMesh);

    // Right holographic pane: "IDEAS PEOPLE IMPACT"
    const rightPaneTex = createHoloTextTexture(
      ['IDEAS', 'PEOPLE', 'IMPACT'],
      '#a855f7',
      'rgba(168, 85, 247, 0.4)',
      true
    );
    texturesToDispose.push(rightPaneTex);

    const rightPaneGeo = new THREE.PlaneGeometry(2.8, 1.4);
    geometriesToDispose.push(rightPaneGeo);
    const rightPaneMat = new THREE.MeshBasicMaterial({
      map: rightPaneTex,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(rightPaneMat);
    const rightPaneMesh = new THREE.Mesh(rightPaneGeo, rightPaneMat);
    rightPaneMesh.position.set(7.5, 3.6, -1.8);
    rightPaneMesh.rotation.y = -0.18;
    scene.add(rightPaneMesh);

    // Far-Right Terminal Pillar: "MORE THAN A HACKATHON"
    const terminalTex = createHoloTextTexture(
      ['MORE', 'THAN', 'A', 'HACKATHON'],
      '#38bdf8',
      'rgba(56, 189, 248, 0.6)',
      true
    );
    texturesToDispose.push(terminalTex);

    const terminalGeo = new THREE.PlaneGeometry(2.0, 2.8);
    geometriesToDispose.push(terminalGeo);
    const terminalMat = new THREE.MeshBasicMaterial({
      map: terminalTex,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(terminalMat);
    const terminalMesh = new THREE.Mesh(terminalGeo, terminalMat);
    terminalMesh.position.set(12.2, 0.2, -1.2);
    terminalMesh.rotation.y = -0.32;
    scene.add(terminalMesh);

    // 8. Cyber Atmospheric Particles
    const particleCount = 200;
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);

    const cCyan = new THREE.Color(0x22d3ee);
    const cViolet = new THREE.Color(0xa855f7);
    const cWhite = new THREE.Color(0xffffff);

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      particlePositions[i3] = (Math.random() - 0.5) * 32;
      particlePositions[i3 + 1] = (Math.random() - 0.5) * 18 + 1;
      particlePositions[i3 + 2] = (Math.random() - 0.5) * 16 - 1;

      const rnd = Math.random();
      const pColor = rnd < 0.6 ? cCyan : rnd < 0.88 ? cViolet : cWhite;
      particleColors[i3] = pColor.r;
      particleColors[i3 + 1] = pColor.g;
      particleColors[i3 + 2] = pColor.b;
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));
    geometriesToDispose.push(particleGeo);

    const particleMat = new THREE.PointsMaterial({
      size: 0.12,
      vertexColors: true,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
    });
    materialsToDispose.push(particleMat);

    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // 9. Parallax Tracking
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handlePointerMove = (event: PointerEvent) => {
      const windowHalfX = window.innerWidth / 2;
      const windowHalfY = window.innerHeight / 2;
      mouseX = (event.clientX - windowHalfX) * 0.0008;
      mouseY = (event.clientY - windowHalfY) * 0.0008;
    };

    window.addEventListener('pointermove', handlePointerMove, { passive: true });

    // 10. Responsive Resize
    const handleResize = () => {
      if (!renderer) return;
      const width = window.innerWidth;
      const height = window.innerHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    };

    window.addEventListener('resize', handleResize, { passive: true });

    // 11. Tab Visibility Handler (0% GPU when inactive)
    let isTabVisible = !document.hidden;
    const handleVisibilityChange = () => {
      isTabVisible = !document.hidden;
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 12. Animation Render Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (!isTabVisible) return;

      const elapsedTime = clock.getElapsedTime();

      if (!prefersReducedMotion) {
        // Damped Parallax Camera Easing
        targetX += (mouseX - targetX) * 0.035;
        targetY += (-mouseY - targetY) * 0.035;

        camera.position.x = targetX * 3.2;
        camera.position.y = 1.2 + targetY * 2.0;
        camera.lookAt(0, 1.2, -4);

        // Continuous Holographic Earth Rotation
        earthMesh.rotation.y = elapsedTime * 0.14;
        gridGlobeMesh.rotation.y = elapsedTime * 0.14;

        // Orbital Ring Revolutions
        ring1.rotation.z = elapsedTime * 0.22;
        ring2.rotation.z = -elapsedTime * 0.18;

        // Animate nodes around the rings
        const nodeAngle1 = elapsedTime * 1.5;
        node1.position.x = Math.cos(nodeAngle1) * 3.9;
        node1.position.y = Math.sin(nodeAngle1) * 3.9;
        node2.position.x = Math.cos(nodeAngle1 + Math.PI) * 3.9;
        node2.position.y = Math.sin(nodeAngle1 + Math.PI) * 3.9;

        const nodeAngle2 = -elapsedTime * 1.2;
        node3.position.x = Math.cos(nodeAngle2) * 4.7;
        node3.position.y = Math.sin(nodeAngle2) * 4.7;

        // Subtle BMSIT badge breathing
        bmsitMesh.position.y = Math.sin(elapsedTime * 1.8) * 0.06;

        // Floating sign bobbing
        leftPaneMesh.position.y = 3.4 + Math.sin(elapsedTime * 1.2) * 0.08;
        rightPaneMesh.position.y = 3.6 + Math.cos(elapsedTime * 1.0) * 0.08;

        // Moving cyber point lights
        cyanLight.position.x = -2 + Math.sin(elapsedTime * 0.6) * 2;
        violetLight.position.x = 6 + Math.cos(elapsedTime * 0.5) * 2;

        // Subtle particle drift
        particleSystem.rotation.y = elapsedTime * 0.018;
      }

      if (renderer) {
        renderer.render(scene, camera);
      }
    };

    animate();

    // 13. Cleanup on Unmount
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('resize', handleResize);
      prefersReducedMotionQuery.removeEventListener('change', handleMotionChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);

      geometriesToDispose.forEach((g) => g.dispose());
      materialsToDispose.forEach((m) => m.dispose());
      texturesToDispose.forEach((t) => t.dispose());

      if (renderer) {
        renderer.dispose();
        if (renderer.domElement && container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
        }
      }
    };
  }, []);

  return (
    <div
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none"
    >
      {/* Three.js Canvas Container */}
      <div ref={containerRef} className="w-full h-full absolute inset-0" />

      {/* Cyber Grid Depth Overlay & Ambient Radial Vignette */}
      <div className="absolute inset-0 bg-radial from-transparent via-[#030712]/35 to-[#030712]/80 pointer-events-none" />

      {/* Static Fallback (if WebGL is disabled or unsupported) */}
      {!hasWebGL && (
        <div className="absolute inset-0 bg-[#030712] pointer-events-none flex items-center justify-center">
          <img
            src="/cyber-control-room.jpg"
            alt="Cyber Control Room"
            className="w-full h-full object-cover opacity-60"
          />
          <div className="absolute inset-0 bg-radial from-transparent via-[#030712]/60 to-[#030712]" />
        </div>
      )}
    </div>
  );
}
