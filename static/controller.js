function joystick(id, callback) {
  const box = document.getElementById(id);
  const stick = box.querySelector('.stick');
  let active = false;
  let cx = 0, cy = 0;

  function center() {
    const r = box.getBoundingClientRect();
    cx = r.left + r.width/2;
    cy = r.top + r.height/2;
  }

  function start(e){
    active = true; center();
    e.preventDefault();
  }
  function end(e){
    active = false;
    stick.style.transform = "translate(-50%,-50%)";
    callback(0,0);
    e.preventDefault();
  }
  function move(e){
    if(!active) return;
    let x,y;
    if(e.touches){
      x=e.touches[0].clientX; y=e.touches[0].clientY;
    } else { x=e.clientX; y=e.clientY; }
    let dx = x-cx, dy = y-cy;
    const R = box.offsetWidth/2;
    let nx = dx/R, ny = dy/R;
    const m = Math.sqrt(nx*nx+ny*ny);
    if(m>1){ nx/=m; ny/=m; }
    const px = nx*(R-30), py=ny*(R-30);
    stick.style.transform=`translate(${px}px,${py}px)`;
    callback(Math.round(nx*100), Math.round(-ny*100));
    e.preventDefault();
  }

  box.addEventListener("mousedown",start);
  window.addEventListener("mousemove",move);
  window.addEventListener("mouseup",end);
  box.addEventListener("touchstart",start,{passive:false});
  window.addEventListener("touchmove",move,{passive:false});
  window.addEventListener("touchend",end,{passive:false});
}

function post(url,obj){
  fetch(url,{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(obj||{})
  });
}

joystick("joy-drive",(x,y)=>post("/api/move",{x,y}));
joystick("joy-cam",(x,y)=>post("/api/camera",{x,y}));

const toggleIds = ["line_track","avoid_obstacles","face_detect","color_detect","color_follow"];

toggleIds.forEach(id=>{
  document.getElementById(id).onchange=()=>{
    const data={};
    toggleIds.forEach(k=>data[k]=document.getElementById(k).checked);
    post("/api/modes",data);
  };
});

document.getElementById("horn").onclick=()=>post("/api/horn");
document.getElementById("stop").onclick=()=>post("/api/stop");

// Speed limit slider
const maxSlider = document.getElementById("max-speed");
const maxLabel  = document.getElementById("max-speed-label");
maxSlider.oninput = () => {
  const v = parseInt(maxSlider.value);
  maxLabel.textContent = v;
  post("/api/settings",{speed_limit:v});
};

// Obstacle distance sliders
const safeSlider = document.getElementById("safe-distance");
const safeLabel  = document.getElementById("safe-distance-label");
safeSlider.oninput = () => {
  let v = parseInt(safeSlider.value);
  safeLabel.textContent = v;
  post("/api/settings",{safe_distance:v});
};

const dangerSlider = document.getElementById("danger-distance");
const dangerLabel  = document.getElementById("danger-distance-label");
dangerSlider.oninput = () => {
  let v = parseInt(dangerSlider.value);
  dangerLabel.textContent = v;
  post("/api/settings",{danger_distance:v});
};

// Keyboard control: WASD + arrows
const keyState = {up:false,down:false,left:false,right:false};

function updateFromKeys(){
  let x = 0, y = 0;
  if(keyState.left)  x -= 100;
  if(keyState.right) x += 100;
  if(keyState.up)    y += 100;
  if(keyState.down)  y -= 100;
  x = Math.max(-100,Math.min(100,x));
  y = Math.max(-100,Math.min(100,y));
  post("/api/move",{x,y});
}

window.addEventListener("keydown",e=>{
  let handled = false;
  switch(e.key){
    case "w": case "W": case "ArrowUp":    if(!keyState.up){keyState.up=true; handled=true;} break;
    case "s": case "S": case "ArrowDown":  if(!keyState.down){keyState.down=true; handled=true;} break;
    case "a": case "A": case "ArrowLeft":  if(!keyState.left){keyState.left=true; handled=true;} break;
    case "d": case "D": case "ArrowRight": if(!keyState.right){keyState.right=true; handled=true;} break;
  }
  if(handled){
    updateFromKeys();
    e.preventDefault();
  }
});

window.addEventListener("keyup",e=>{
  let handled = false;
  switch(e.key){
    case "w": case "W": case "ArrowUp":    if(keyState.up){keyState.up=false; handled=true;} break;
    case "s": case "S": case "ArrowDown":  if(keyState.down){keyState.down=false; handled=true;} break;
    case "a": case "A": case "ArrowLeft":  if(keyState.left){keyState.left=false; handled=true;} break;
    case "d": case "D": case "ArrowRight": if(keyState.right){keyState.right=false; handled=true;} break;
  }
  if(handled){
    updateFromKeys();
    e.preventDefault();
  }
});

// Mini 3D car (Three.js if available, fallback otherwise)
let carScene = null, carCamera = null, carRenderer = null, carMesh = null;

function init3DCar(){
  if(typeof THREE === "undefined") return false;

  const canvas = document.getElementById("car3d-canvas");
  carRenderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true});
  carRenderer.setSize(canvas.width, canvas.height, false);

  carScene = new THREE.Scene();
  carScene.background = null;

  carCamera = new THREE.PerspectiveCamera(45, canvas.width/canvas.height, 0.1, 100);
  carCamera.position.set(0, 4, 10);
  carCamera.lookAt(0, 0, 0);

  const light = new THREE.DirectionalLight(0xffffff, 1.1);
  light.position.set(5, 10, 7);
  carScene.add(light);
  carScene.add(new THREE.AmbientLight(0x404040, 0.8));

  const bodyGeom = new THREE.BoxGeometry(4, 1, 7);
  const bodyMat = new THREE.MeshStandardMaterial({color:0x2e63ff});
  const body = new THREE.Mesh(bodyGeom, bodyMat);

  const cabGeom = new THREE.BoxGeometry(3, 1.2, 3);
  const cabMat = new THREE.MeshStandardMaterial({color:0x88a2ff});
  const cab = new THREE.Mesh(cabGeom, cabMat);
  cab.position.y = 1.0;
  cab.position.z = -1;

  const grp = new THREE.Group();
  grp.add(body);
  grp.add(cab);

  carMesh = grp;
  carScene.add(carMesh);

  function render() {
    requestAnimationFrame(render);
    if(carRenderer && carScene && carCamera){
      carRenderer.render(carScene, carCamera);
    }
  }
  render();
  return true;
}

let use3DCar = false;
if(init3DCar()){
  use3DCar = true;
}

// Telemetry + HUD updates for controller (not charts)
function tickController(){
  fetch("/api/status").then(r=>r.json()).then(d=>{
    const speed = d.speed || 0;
    document.getElementById("speed-val").textContent = speed;

    const needle = document.getElementById("needle");
    const clamped = Math.max(0, Math.min(100, speed));
    const angle = -90 + (clamped / 100) * 180;
    needle.setAttribute("transform", "rotate(" + angle + " 100 100)");

    document.getElementById("dist").textContent = d.distance;
    document.getElementById("linestate").textContent = "["+d.line.join(", ")+"]";

    let mode="Manual";
    if(d.modes.line_track) mode="Line track";
    if(d.modes.avoid_obstacles) mode="Avoid obstacles";
    if(d.modes.color_follow) mode="Color follow";
    document.getElementById("mode").textContent=mode;

    toggleIds.forEach(k=>{
      document.getElementById(k).checked = d.modes[k];
    });

    // sync sliders from backend if changed
    if(typeof d.speed_limit !== "undefined"){
      maxSlider.value = d.speed_limit;
      maxLabel.textContent = d.speed_limit;
    }
    if(typeof d.safe_distance !== "undefined"){
      safeSlider.value = d.safe_distance;
      safeLabel.textContent = d.safe_distance;
    }
    if(typeof d.danger_distance !== "undefined"){
      dangerSlider.value = d.danger_distance;
      dangerLabel.textContent = d.danger_distance;
    }

    // Car motion HUD
    const motion = d.motion || "stop";
    const motionText = document.getElementById("motion-text");
    motionText.textContent = motion.charAt(0).toUpperCase() + motion.slice(1);

    if(use3DCar && carMesh){
      if(motion === "left"){
        carMesh.rotation.y = 0.5;
      } else if(motion === "right"){
        carMesh.rotation.y = -0.5;
      } else {
        carMesh.rotation.y = 0.0;
      }
      carMesh.position.y = 0.1 * Math.sin(Date.now()/200) * (clamped/100);
    } else {
      const canvas = document.getElementById("car3d-canvas");
      let rot = 0;
      if(motion === "left") rot = -10;
      else if(motion === "right") rot = 10;
      canvas.style.transform = "perspective(300px) rotateY("+rot+"deg)";
    }

    // Radar HUD using thresholds
    const radar = document.getElementById("radar");
    const radarLabel = document.getElementById("radar-label");
    const dist = d.distance || 0;
    const safeDist = d.safe_distance || 40;
    const dangerDist = d.danger_distance || 20;

    radar.classList.remove("radar-safe","radar-close","radar-danger");
    if(dist <= 0 || dist > safeDist){
      radar.classList.add("radar-safe");
      radarLabel.textContent = "Safe";
    } else if(dist > dangerDist){
      radar.classList.add("radar-close");
      radarLabel.textContent = "Obstacle";
    } else {
      radar.classList.add("radar-danger");
      radarLabel.textContent = "Too close";
    }

    // Line HUD
    const lineDot = document.getElementById("line-car-dot");
    const lineStatusText = document.getElementById("line-status");
    const lineState = d.line_state || "stop";

    let label = "No line";
    let offset = 50;
    if(lineState === "forward"){
      label = "Center";
      offset = 50;
    } else if(lineState === "left"){
      label = "Left";
      offset = 35;
    } else if(lineState === "right"){
      label = "Right";
      offset = 65;
    }
    lineStatusText.textContent = label;
    lineDot.style.left = offset + "%";
  }).catch(()=>{});
}
setInterval(tickController,200);
