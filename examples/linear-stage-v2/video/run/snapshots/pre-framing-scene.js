import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { gsap } from 'gsap';

const WIDTH = 1280, HEIGHT = 720, DURATION = 24;
const BG = 0xedf0f1, ACCENT = 0x137785;
const clamp = value => Math.min(1, Math.max(0, value));
const smooth = value => { const p = clamp(value); return p*p*(3-2*p); };
const mix = (a,b,t) => a+(b-a)*t;
const canvas = document.getElementById('stage-canvas');
const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:false, preserveDrawingBuffer:true});
renderer.setSize(WIDTH,HEIGHT,false);
renderer.setPixelRatio(1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.18;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.VSMShadowMap;
renderer.autoClear = false;
const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
const environment = pmrem.fromScene(room,0.04).texture;
room.dispose();

const camera = new THREE.OrthographicCamera(-200,200,112.5,-112.5,1,2000);
camera.up.set(0,0,1);
const comparisonCamera = new THREE.OrthographicCamera(-210,210,48.2,-48.2,1,2000);
comparisonCamera.up.set(0,0,1);
comparisonCamera.position.set(30,-500,180);
comparisonCamera.lookAt(30,0,23);
const models = [];

function makeScene() {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BG);
  scene.environment = environment;
  scene.environmentIntensity = 1.05;
  scene.add(new THREE.HemisphereLight(0xfafcff,0x758185,0.45));
  const key = new THREE.DirectionalLight(0xfff7ee,3.5);
  key.position.set(-120,-160,320);
  key.castShadow = true;
  key.shadow.mapSize.set(1024,1024);
  key.shadow.camera.left = -330;
  key.shadow.camera.right = 330;
  key.shadow.camera.top = 220;
  key.shadow.camera.bottom = -220;
  key.shadow.camera.near = 1;
  key.shadow.camera.far = 900;
  key.shadow.normalBias = 0.25;
  key.shadow.bias = -0.00008;
  key.shadow.radius = 4;
  key.shadow.blurSamples = 8;
  key.target.position.set(20,0,20);
  scene.add(key,key.target);
  const fill = new THREE.DirectionalLight(0xd5e7fa,1.25);
  fill.position.set(220,190,150);
  scene.add(fill);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(2000,2000),new THREE.ShadowMaterial({color:0x26313c,opacity:0.18}));
  floor.position.z = -0.6;
  floor.receiveShadow = true;
  scene.add(floor);
  return scene;
}

function loadJSON(path) {
  return new Promise((resolve,reject) => new THREE.FileLoader().setResponseType('json').load(path,resolve,undefined,reject));
}
function loadBytes(path) {
  return new Promise((resolve,reject) => new THREE.FileLoader().setResponseType('arraybuffer').load(path,resolve,undefined,reject));
}

async function loadModel(travel) {
  const data = await loadJSON(`assets/stage-${travel}.json`);
  const compressed = await loadBytes(`assets/stage-${travel}.bin.gz`);
  const buffer = await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const scene = makeScene();
  const partObjects = data.parts.map(entry => {
    const spec = entry.mesh;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(buffer,spec.position_offset,spec.vertex_count*3),3));
    geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer,spec.index_offset,spec.index_count),1));
    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();
    const color = new THREE.Color().setRGB(...entry.color_rgba.slice(0,3),THREE.SRGBColorSpace);
    const material = new THREE.MeshStandardMaterial({color,metalness:entry.material.metalness,roughness:entry.material.roughness,envMapIntensity:1.0});
    const mesh = new THREE.Mesh(geometry,material);
    mesh.name = entry.name;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    const rotating = ['screw','coupling','motor_shaft'].includes(entry.mechanism);
    if (rotating) { geometry.translate(0,0,-28); mesh.position.z=28; }
    mesh.userData = {entry,rotating,home:mesh.position.clone()};
    scene.add(mesh);
    return mesh;
  });
  // Dimensional annotations are separate from the STEP geometry.
  const dimensions = new THREE.Group();
  const lineMaterial = new THREE.LineBasicMaterial({color:ACCENT});
  const y = -68,z = 4,half = travel/2;
  const points = [[-half,y,z],[half,y,z],[-half,y,z],[-half+4,y-2,z],[half,y,z],[half-4,y-2,z]];
  const geometry = new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(...p)));
  dimensions.add(new THREE.LineSegments(geometry,lineMaterial));
  dimensions.visible=false;
  scene.add(dimensions);
  return {data,scene,parts:partObjects,dimensions};
}

function pose(model,position=0,explodeTime=null) {
  const degrees = model.data.motion.rotation_deg_per_mm;
  for (const mesh of model.parts) {
    const {entry,rotating,home} = mesh.userData;
    mesh.position.copy(home);
    mesh.rotation.set(0,0,0);
    if (entry.moving) mesh.position.x += position;
    if (rotating) mesh.rotation.x = THREE.MathUtils.degToRad(position*degrees);
    if (explodeTime !== null) {
      const fraction = smooth((explodeTime-(entry.explode.stage-1)*0.44)/1.25);
      const [x,y,z] = entry.explode.offset_mm;
      mesh.position.x += x*fraction;
      mesh.position.y += y*fraction;
      mesh.position.z += z*fraction;
    }
  }
}

function carriagePosition(t) {
  if (t<3 || t>=8) return 0;
  const segments = [[3,4.1,0,-40],[4.1,6.7,-40,40],[6.7,8,40,0]];
  const segment=segments.find(([a,b])=>t>=a&&t<=b);
  return segment ? mix(segment[2],segment[3],smooth((t-segment[0])/(segment[1]-segment[0]))) : 0;
}

function cameraPose(t) {
  const explode = smooth((t-8)/1.7) * (1-smooth((t-16.2)/1.4));
  const azimuth = THREE.MathUtils.degToRad(mix(-69,-55,smooth(t/8)));
  const elevation = THREE.MathUtils.degToRad(mix(31,29,explode));
  const radius=520;
  const target = new THREE.Vector3(mix(28,50,explode),0,mix(22,52,explode));
  camera.position.set(target.x+radius*Math.cos(azimuth)*Math.cos(elevation),target.y+radius*Math.sin(azimuth)*Math.cos(elevation),target.z+radius*Math.sin(elevation));
  camera.lookAt(target);
  const span = mix(205,270,explode);
  camera.top=span/2;camera.bottom=-span/2;
  camera.left=-span*WIDTH/HEIGHT/2;camera.right=-camera.left;
  camera.updateProjectionMatrix();
}

function setCopy(t,position) {
  const index=t<3?0:t<8?1:t<18?2:3;
  document.getElementById('headline').textContent=['Screw-driven linear stage','Rotation becomes linear travel','Inside the assembly','Longer travel. Same interfaces.'][index];
  document.getElementById('counter').textContent=`0${index+1} / 04`;
  document.getElementById('note').textContent=['Parametric CAD · 4 mm lead','4 mm / revolution','Fasteners → platform → guides → drive','80 → 120 mm · common scale'][index];
  document.getElementById('measure').textContent=index===1?`x = ${position.toFixed(1)} mm`:'';
  document.getElementById('comparison-labels').style.opacity=index===3?'1':'0';
}

function renderAt(time) {
  if (models.length<2) return;
  const t=Math.min(DURATION,Math.max(0,time));
  const position=carriagePosition(t);
  setCopy(t,position);
  renderer.setScissorTest(false);
  renderer.setViewport(0,0,WIDTH,HEIGHT);
  renderer.clear();
  if (t<18) {
    let exploded=null;
    if(t>=8.5&&t<14) exploded=Math.min(3.5,t-8.5);
    else if(t>=14&&t<18) exploded=Math.max(0,3.5-(t-14));
    pose(models[0],position,exploded);
    models[0].dimensions.visible=false;
    cameraPose(t);
    renderer.render(models[0].scene,camera);
  } else {
    renderer.setScissorTest(true);
    const progress=smooth((t-18.8)/4.2);
    for (let i=0;i<2;i++) {
      const model=models[i];
      pose(model,mix(-model.data.travel_mm/2,model.data.travel_mm/2,progress));
      model.dimensions.visible=true;
      const y=i===0?342:92;
      renderer.setViewport(0,y,WIDTH,280);
      renderer.setScissor(0,y,WIDTH,280);
      renderer.clear();
      renderer.render(model.scene,comparisonCamera);
    }
    renderer.setScissorTest(false);
  }
  window.__stageState = {time:t,carriage_mm:position,phase:t<3?'assembly':t<8?'motion':t<18?'exploded':'comparison'};
}

const tl=gsap.timeline({paused:true});
tl.fromTo('#progress',{scaleX:0},{scaleX:1,duration:DURATION,ease:'none'},0);
window.__timelines = window.__timelines || {};
window.stageTimeline=tl;
window.addEventListener('hf-seek',event=>renderAt(event.detail.time));
window.__hf=window.__hf||{};
window.__hf.buildReady=window.__hf.buildReady||{};
window.__hf.buildReady['cad-stage']=Promise.all([loadModel(80),loadModel(120)]).then(loaded=>{
  models.push(...loaded);
  renderAt(window.__hfThreeTime||0);
});
window.stageRenderAt=renderAt;
window.stageScene={renderer,camera,models,pose,cameraPose};
