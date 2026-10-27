import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { gsap } from 'gsap';

const WIDTH = 1280, HEIGHT = 720, DURATION = 12;
const BG = 0xf0f2f3;
const clamp = value => Math.min(1, Math.max(0, value));
const smooth = value => { const p = clamp(value); return p*p*(3-2*p); };
const mix = (a,b,t) => a+(b-a)*t;
const renderer = new THREE.WebGLRenderer({canvas:document.getElementById('joint-canvas'),antialias:true,alpha:false,preserveDrawingBuffer:true});
renderer.setSize(WIDTH,HEIGHT,false);
renderer.setPixelRatio(1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.VSMShadowMap;
renderer.autoClear = false;
const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
const environment = pmrem.fromScene(room,0.04).texture;
room.dispose();
const camera = new THREE.OrthographicCamera(-140,140,78.75,-78.75,1,1600);
camera.up.set(0,0,1);
const comparisonCamera = new THREE.OrthographicCamera(-91,91,78,-78,1,1600);
comparisonCamera.up.set(0,0,1);
comparisonCamera.position.set(650,-160,115);
comparisonCamera.lookAt(0,0,0);
const models = [];

function makeScene() {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BG);
  scene.environment = environment;
  scene.environmentIntensity = 1.1;
  scene.add(new THREE.HemisphereLight(0xffffff,0x83909a,0.45));
  const key = new THREE.DirectionalLight(0xfff5e9,2.4);
  key.position.set(120,-190,300);
  key.castShadow = true;
  key.shadow.mapSize.set(2048,2048);
  key.shadow.camera.left=-245;key.shadow.camera.right=245;
  key.shadow.camera.top=160;key.shadow.camera.bottom=-160;
  key.shadow.camera.near=1;key.shadow.camera.far=900;
  key.shadow.normalBias=0.18;key.shadow.bias=-0.00008;
  key.shadow.radius=7;key.shadow.blurSamples=12;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xe0edff,0.9);
  fill.position.set(-160,140,180);
  scene.add(fill);
  const front = new THREE.DirectionalLight(0xffffff,0.4);
  front.position.set(140,-140,60);
  scene.add(front);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(1600,1600),new THREE.ShadowMaterial({color:0x293849,opacity:0.13}));
  floor.position.z=-55.3;floor.receiveShadow=true;
  scene.add(floor);
  return scene;
}

function loadJSON(path) { return new Promise((resolve,reject)=>new THREE.FileLoader().setResponseType('json').load(path,resolve,undefined,reject)); }
function loadBytes(path) { return new Promise((resolve,reject)=>new THREE.FileLoader().setResponseType('arraybuffer').load(path,resolve,undefined,reject)); }

function machinedFinish(material) {
  // Shallow turning marks affect only the rendered surface normal, not CAD geometry.
  material.onBeforeCompile = shader => {
    const varyings = 'varying vec3 vMachinePosition; varying vec3 vRadialView; varying vec3 vAxisView; varying vec3 vObjectNormal;\n';
    shader.vertexShader = varyings + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
      vMachinePosition = position;
      vec3 radial = vec3(0.0, position.y, position.z);
      vRadialView = normalMatrix * radial / max(length(radial), 0.001);
      vAxisView = normalMatrix * vec3(1.0, 0.0, 0.0);
      vObjectNormal = normal;`);
    shader.fragmentShader = varyings + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
      float faceWeight = step(0.8, abs(vObjectNormal.x));
      float groovePhase = mix(vMachinePosition.x, length(vMachinePosition.yz), faceWeight) * 17.0;
      float grooveFilter = 1.0 / (1.0 + pow(fwidth(groovePhase) * 0.7, 2.0));
      normal = normalize(normal + mix(vAxisView, vRadialView, faceWeight) * (0.025 * sin(groovePhase) * grooveFilter));`);
  };
  material.customProgramCacheKey = () => 'subtle-turning-marks-v1';
  return material;
}

async function loadModel(bore) {
  const data = await loadJSON(`assets/joint-${bore}.json`);
  const compressed = await loadBytes(`assets/joint-${bore}.bin.gz`);
  const buffer = await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const scene = makeScene();
  function geometryFor(spec) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(buffer,spec.position_offset,spec.vertex_count*3),3));
    geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer,spec.index_offset,spec.index_count),1));
    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();
    return geometry;
  }
  const parts = data.parts.map(entry=>{
    const color = new THREE.Color().setRGB(...entry.color_rgba.slice(0,3),THREE.SRGBColorSpace);
    const material = new THREE.MeshStandardMaterial({color,metalness:entry.material.metalness,roughness:Math.max(0.2,entry.material.roughness),envMapIntensity:1.05});
    if(entry.material.name==='aluminium') machinedFinish(material);
    const full = new THREE.Mesh(geometryFor(entry.mesh),material);
    full.name=entry.name;full.castShadow=true;full.receiveShadow=true;
    scene.add(full);
    let cut=null;
    if(entry.cut_mesh) {
      cut=new THREE.Mesh(geometryFor(entry.cut_mesh),material);
      cut.name=entry.name+'-section';cut.castShadow=true;cut.receiveShadow=true;
      cut.visible=false;scene.add(cut);
    }
    return {entry,full,cut};
  });
  return {data,scene,parts};
}

function pose(model,section=false,explosion=0) {
  for(const {entry,full,cut} of model.parts) {
    full.visible=!(section&&entry.cutaway);
    if(cut) cut.visible=section;
    const stage=entry.explode?.stage??1;
    const factor=smooth((explosion-(stage-1)*0.045)/0.75);
    const offset=entry.explode?.offset_mm??[0,0,0];
    full.position.set(...offset).multiplyScalar(factor);
    if(cut) cut.position.copy(full.position);
  }
}

function cameraPose(t,exploded) {
  const azimuth = THREE.MathUtils.degToRad(mix(-58,-68,smooth(t/8.5)));
  const elevation = THREE.MathUtils.degToRad(mix(27,22,exploded));
  const target = new THREE.Vector3(mix(1,0,exploded),0,mix(0,-1,exploded));
  const radius=560;
  camera.position.set(target.x+radius*Math.cos(azimuth)*Math.cos(elevation),target.y+radius*Math.sin(azimuth)*Math.cos(elevation),target.z+radius*Math.sin(elevation));
  camera.lookAt(target);
  const span=mix(157,242,exploded);
  camera.top=span/2;camera.bottom=-span/2;
  camera.left=-span*WIDTH/HEIGHT/2;camera.right=-camera.left;
  camera.updateProjectionMatrix();
}

function setCopy(t) {
  const comparison=t>=9;
  const exploded=t>=4.2&&t<9;
  const section=t<3;
  document.getElementById('phase').textContent=comparison?'Bore revision':exploded?'Exploded view':section?'Section view':'Assembly';
  document.getElementById('note').textContent=comparison?'20 → 30 mm through-bore · same outer envelope':'';
  document.getElementById('comparison').style.opacity=comparison?'1':'0';
  document.getElementById('labels').style.opacity=t>=5.9&&t<7.8?'1':'0';
}

function renderAt(time) {
  if(models.length<2) return;
  const t=Math.min(DURATION,Math.max(0,time));
  setCopy(t);
  renderer.setScissorTest(false);
  renderer.setViewport(0,0,WIDTH,HEIGHT);
  renderer.clear();
  let explosion=0;
  if(t>=4.2&&t<7.7) explosion=smooth((t-4.2)/1.5);
  else if(t>=7.7&&t<9) explosion=1-smooth((t-7.7)/1.3);
  if(t<9) {
    pose(models[0],t<3||t>=4.2,explosion);
    cameraPose(t,explosion);
    renderer.render(models[0].scene,camera);
  } else {
    renderer.setScissorTest(true);
    for(let i=0;i<2;i++) {
      pose(models[i],false,0);
      // Identical camera and viewport dimensions preserve the comparison scale.
      renderer.setViewport(i*WIDTH/2,100,WIDTH/2,548);
      renderer.setScissor(i*WIDTH/2,100,WIDTH/2,548);
      renderer.clear();
      renderer.render(models[i].scene,comparisonCamera);
    }
    renderer.setScissorTest(false);
  }
  window.__jointState={time:t,phase:t<3?'section':t<4.2?'assembly':t<9?'exploded':'comparison',explosion};
}

const tl=gsap.timeline({paused:true});
tl.fromTo('#progress',{scaleX:0},{scaleX:1,duration:DURATION,ease:'none'},0);
window.__timelines=window.__timelines||{};
window.jointTimeline=tl;
window.addEventListener('hf-seek',event=>renderAt(event.detail.time));
window.__hf=window.__hf||{};
window.__hf.buildReady=window.__hf.buildReady||{};
window.__hf.buildReady['cad-joint']=Promise.all([loadModel(20),loadModel(30)]).then(loaded=>{
  models.push(...loaded);
  renderAt(window.__hfThreeTime||0);
});
window.jointRenderAt=renderAt;
window.jointScene={renderer,camera,comparisonCamera,models,pose,cameraPose};
