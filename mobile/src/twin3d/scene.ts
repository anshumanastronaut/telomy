// 3D digital twin — real human anatomy (BodyParts3D, © DBCLS, CC BY 4.0: organs segmented from a CT-scanned body),
// rendered with three.js in a WebView. Physically based organs in true anatomical tones under environment light,
// a frosted translucent skin so you can see inside, ACES tone mapping and a soft bloom. Your health status is an
// emissive halo on each organ (in range / watch / out of range) — the anatomy itself keeps its real colours.
// Orbit with inertia, pinch zoom, tap an organ to focus it, toggle layers (skin / organs / skeleton / vessels).
import { THREE_SRC } from './threeSource.generated';

export type OrganId = 'brain' | 'lungs' | 'heart' | 'vessels' | 'liver' | 'stomach' | 'pancreas' | 'kidneys' | 'intestines' | 'bladder' | 'skeleton';
export type OrganStatus = 'ok' | 'watch' | 'high' | 'none';
export type Layers = { skin: boolean; organs: boolean; skeleton: boolean; vessels: boolean };

const SCENE_JS = String.raw`
const post = (m) => window.ReactNativeWebView && window.ReactNativeWebView.postMessage(JSON.stringify(m));
window.onerror = (msg, src, line) => post({ type: 'error', message: String(msg) + ' @' + line });
(async () => {
const T = await import(URL.createObjectURL(new Blob([window.__THREE_SRC], { type: 'text/javascript' })));
const W = () => window.innerWidth, H = () => window.innerHeight;

// ---------- renderer, camera, light
const renderer = new T.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.setSize(W(), H());
renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.08; renderer.outputColorSpace = T.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new T.Scene(); scene.background = new T.Color('#06090A');
const pmrem = new T.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new T.RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.55;
scene.add(new T.HemisphereLight('#BFD9E8', '#2A1E18', 0.7));
const key = new T.DirectionalLight('#FFF4EA', 2.2); key.position.set(1.2, 2.6, 2.4); scene.add(key);
const rim = new T.DirectionalLight('#7FD6FF', 1.6); rim.position.set(-1.6, 1.8, -2.2); scene.add(rim);
const fill = new T.DirectionalLight('#FFD9C2', 0.5); fill.position.set(-2, 0.6, 1.4); scene.add(fill);

const camera = new T.PerspectiveCamera(30, W() / H(), 0.02, 30);
camera.position.set(0.55, 1.15, 3.7);
const controls = new T.OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.92, 0); controls.enableDamping = true; controls.dampingFactor = 0.08; controls.enablePan = false;
controls.rotateSpeed = 0.75; controls.zoomSpeed = 0.9; controls.minDistance = 0.35; controls.maxDistance = 5;
controls.minPolarAngle = 0.25; controls.maxPolarAngle = Math.PI - 0.25; controls.autoRotate = true; controls.autoRotateSpeed = 0.55;
let idleAt = 0; controls.addEventListener('start', () => { controls.autoRotate = false; idleAt = performance.now(); fly = null; });
controls.addEventListener('end', () => { idleAt = performance.now(); });

// ---------- post: bloom only on bright emissive (status halos), gentle
const composer = new T.EffectComposer(renderer);
composer.addPass(new T.RenderPass(scene, camera));
const bloom = new T.UnrealBloomPass(new T.Vector2(W(), H()), 0.32, 0.55, 0.93)   // bloom only catches the status glow; composer.addPass(bloom);
composer.addPass(new T.OutputPass());

// ---------- floor: soft contact shadow + thin rings
const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
const grd = g.createRadialGradient(128, 128, 0, 128, 128, 128); grd.addColorStop(0, 'rgba(0,0,0,0.75)'); grd.addColorStop(1, 'rgba(0,0,0,0)');
g.fillStyle = grd; g.fillRect(0, 0, 256, 256);
const shadow = new T.Mesh(new T.PlaneGeometry(0.9, 0.9), new T.MeshBasicMaterial({ map: new T.CanvasTexture(c), transparent: true, depthWrite: false }));
shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.002; scene.add(shadow);
for (const [r, o] of [[0.42, 0.22], [0.62, 0.1]]) { const ring = new T.Mesh(new T.RingGeometry(r, r + 0.003, 128), new T.MeshBasicMaterial({ color: '#5CC9A7', transparent: true, opacity: o, side: T.DoubleSide })); ring.rotation.x = -Math.PI / 2; ring.position.y = 0.003; scene.add(ring); }

// ---------- materials
const ANAT = { brain: '#D8A7A3', heart: '#8E1A22', lungs: '#E2A1A5', liver: '#6E2A20', stomach: '#C98478', pancreas: '#E0B074',
  kidneys: '#7E2A27', intestines: '#D89A8C', bladder: '#D9B27E', vessels: '#B0131D', skeleton: '#BFB096' };   // bone toned down so it never glares
const STATUS = { ok: new T.Color('#4FD08F'), watch: new T.Color('#F2B94B'), high: new T.Color('#FF6B57'), none: new T.Color('#000000') };
const organMat = (hex) => new T.MeshPhysicalMaterial({ color: hex, roughness: 0.42, metalness: 0, clearcoat: 0.55, clearcoatRoughness: 0.32,
  sheen: 0.35, sheenRoughness: 0.6, sheenColor: new T.Color('#FFE6E0'), emissive: new T.Color('#000'), emissiveIntensity: 0, transparent: true, opacity: 1 });
// frosted translucent skin: fresnel rim, faint fill, never hides the organs
const skinMat = new T.ShaderMaterial({
  uniforms: { color: { value: new T.Color('#CFE6EE') }, fade: { value: 1 } }, transparent: true, depthWrite: false, side: T.FrontSide,
  vertexShader: 'varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }',
  fragmentShader: 'uniform vec3 color; uniform float fade; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(1.0-abs(dot(normalize(vN),normalize(vV))), 2.6); gl_FragColor = vec4(color*(0.55+f*0.9), (0.035+f*0.42)*fade); }',
});
// status halo: back-face shell slightly larger than the organ, additive, in the status colour
const haloMat = (col) => new T.ShaderMaterial({ uniforms: { color: { value: col.clone() }, gain: { value: 1 } }, transparent: true, depthWrite: false, side: T.BackSide, blending: T.AdditiveBlending,
  vertexShader: 'varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix*vec4(position + normal*0.004,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }',
  fragmentShader: 'uniform vec3 color; uniform float gain; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(1.0-abs(dot(normalize(vN),normalize(vV))), 1.6); gl_FragColor = vec4(color*f*1.6*gain, f*gain); }' });

// ---------- load the anatomy
const res = await fetch(window.__GLB_URL); if (!res.ok) throw new Error('anatomy model ' + res.status);
const bin = await res.arrayBuffer();
const gltf = await new Promise((res, rej) => new T.GLTFLoader().parse(bin, '', res, rej));
const root = gltf.scene; scene.add(root);
const organs = {}; let skin = null;
const meshes = []; root.traverse((o) => { if (o.isMesh) meshes.push(o); });   // collect first: we add halo children below
meshes.forEach((o) => {
  let n = o; while (n && !ANAT[n.name] && n.name !== 'skin') n = n.parent;
  const id = n ? n.name : o.name;
  o.geometry.computeVertexNormals();
  if (id === 'skin') { o.material = skinMat; o.renderOrder = 10; skin = o; return; }
  if (!ANAT[id]) return;
  o.material = organMat(ANAT[id]); o.userData.organ = id;
  if (id === 'skeleton') { o.material.roughness = 0.75; o.material.clearcoat = 0.05; o.material.sheen = 0; }
  const halo = new T.Mesh(o.geometry, haloMat(STATUS.none)); halo.visible = false; halo.renderOrder = 5; o.add(halo);
  (organs[id] = organs[id] || []).push(o);
});
const centerOf = (id) => { const b = new T.Box3(); for (const m of organs[id] || []) b.expandByObject(m); return { c: b.getCenter(new T.Vector3()), r: b.getSize(new T.Vector3()).length() }; };

// ---------- state from the app
let status = {}, selected = null, layers = { skin: true, organs: true, skeleton: true, vessels: true }, fly = null;
const layerOf = (id) => id === 'skeleton' ? 'skeleton' : id === 'vessels' ? 'vessels' : 'organs';
window.setStatus = (s) => { status = s || {}; };
window.setLayers = (l) => { layers = { ...layers, ...(l || {}) }; };
window.select = (id) => {
  selected = id && organs[id] ? id : null; controls.autoRotate = false; idleAt = performance.now();
  if (selected) { const { c, r } = centerOf(selected); fly = { target: c, dist: Math.max(0.45, r * 2.6) }; }
  else fly = { target: new T.Vector3(0, 0.92, 0), dist: 3.75 };
};

// ---------- tap to select (a drag rotates; a short still tap selects)
const ray = new T.Raycaster(), ndc = new T.Vector2(); let down = null;
renderer.domElement.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 7 || performance.now() - down.t > 450) return;
  ndc.set((e.clientX / W()) * 2 - 1, -(e.clientY / H()) * 2 + 1); ray.setFromCamera(ndc, camera);
  const targets = Object.entries(organs).filter(([id]) => layers[layerOf(id)]).flatMap(([, ms]) => ms);
  const hit = ray.intersectObjects(targets, false)[0];
  const id = hit ? hit.object.userData.organ : null;
  window.select(id === selected ? null : id); post({ type: 'select', organ: selected });
});

window.addEventListener('resize', () => { renderer.setSize(W(), H()); composer.setSize(W(), H()); camera.aspect = W() / H(); camera.updateProjectionMatrix(); });
const clock = new T.Clock(), tmp = new T.Vector3();
renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
  if (!controls.autoRotate && !selected && !fly && performance.now() - idleAt > 7000) controls.autoRotate = true;
  if (fly) {                                            // ease the orbit target + distance toward the focus
    controls.target.lerp(fly.target, 0.09);
    const d = camera.position.distanceTo(controls.target), nd = d + (fly.dist - d) * 0.09;
    tmp.subVectors(camera.position, controls.target).setLength(nd); camera.position.copy(controls.target).add(tmp);
    if (controls.target.distanceTo(fly.target) < 0.002 && Math.abs(nd - fly.dist) < 0.004) fly = null;
  }
  for (const [id, ms] of Object.entries(organs)) {
    const s = status[id] || 'none', on = layers[layerOf(id)], focus = !selected || selected === id;
    const pulse = s === 'high' ? 0.75 + 0.25 * Math.sin(t * 3.0) : 1;
    for (const m of ms) {
      m.visible = on;
      // bone is a see-through frame by default (organs visible through the ribs, like a layered atlas); solid when you pick it
      const base = id === 'skeleton' && selected !== 'skeleton' ? 0.32 : 1;
      m.material.opacity += ((focus ? base : 0.08) - m.material.opacity) * 0.15; m.material.depthWrite = m.material.opacity > 0.9;
      m.material.emissive.copy(STATUS[s]); m.material.emissiveIntensity = s === 'none' ? 0 : (s === 'ok' ? 0.06 : s === 'watch' ? 0.32 : 0.55) * pulse * (focus ? 1 : 0.2);
      const h = m.children[0]; h.visible = on && s !== 'none' && s !== 'ok' && focus;
      if (h.visible) { h.material.uniforms.color.value.copy(STATUS[s]); h.material.uniforms.gain.value = (s === 'high' ? 0.9 : 0.55) * pulse; }
    }
  }
  if (skin) { skin.visible = layers.skin; skin.material.uniforms.fade.value += ((selected ? 0.35 : 1) - skin.material.uniforms.fade.value) * 0.12; }
  controls.update(); composer.render();
});
post({ type: 'ready' });
})().catch((e) => post({ type: 'error', message: String(e && e.message || e) }));
`;

/** Full HTML document for the WebView. The three runtime is embedded; the anatomy model (2.6 MB) is fetched from the
 *  Telomy server and cached, so it never bloats the app bundle. */
export function sceneHtml(glbUrl: string): string {
  const esc = (s: string) => s.replace(/<\//g, '<\\/');
  return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>html,body{margin:0;height:100%;overflow:hidden;background:#06090A;-webkit-user-select:none;-webkit-tap-highlight-color:transparent;touch-action:none}canvas{display:block}</style></head>
<body><script>window.__THREE_SRC=${esc(JSON.stringify(THREE_SRC))};window.__GLB_URL=${JSON.stringify(glbUrl)};</script><script type="module">${esc(SCENE_JS)}</script></body></html>`;
}
