const CB_MATRICES = {
  Protanopia: [
    [0.56667, 0.43333, 0.0],
    [0.55833, 0.44167, 0.0],
    [0.0, 0.24167, 0.75833],
  ],
  Deuteranopia: [
    [0.625, 0.375, 0.0],
    [0.7, 0.3, 0.0],
    [0.0, 0.3, 0.7],
  ],
  Tritanopia: [
    [0.95, 0.05, 0.0],
    [0.0, 0.43333, 0.56667],
    [0.0, 0.475, 0.525],
  ],
};

function srgbToLinear(v){
  v = Math.min(1, Math.max(0, v));
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}
function linearToSrgb(v){
  v = Math.min(1, Math.max(0, v));
  return v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1/2.4) - 0.055;
}

function applySimulationToImageData(imgData, type, severity){
  const data = imgData.data;
  const m = CB_MATRICES[type];
  if(!m) return imgData;
  const s = Math.min(1, Math.max(0, severity));

  for(let i=0;i<data.length;i+=4){
    let r = data[i] / 255;
    let g = data[i+1] / 255;
    let b = data[i+2] / 255;

    // to linear
    let rl = srgbToLinear(r);
    let gl = srgbToLinear(g);
    let bl = srgbToLinear(b);

    // matrix in linear space
    const tl_r = rl * m[0][0] + gl * m[0][1] + bl * m[0][2];
    const tl_g = rl * m[1][0] + gl * m[1][1] + bl * m[1][2];
    const tl_b = rl * m[2][0] + gl * m[2][1] + bl * m[2][2];

    // blend severity
    const bl_r = (1 - s) * rl + s * tl_r;
    const bl_g = (1 - s) * gl + s * tl_g;
    const bl_b = (1 - s) * bl + s * tl_b;

    // back to srgb
    data[i]   = Math.round(255 * linearToSrgb(bl_r));
    data[i+1] = Math.round(255 * linearToSrgb(bl_g));
    data[i+2] = Math.round(255 * linearToSrgb(bl_b));
    // alpha unchanged
  }
  return imgData;
}

function fitDrawImage(ctx, img, canvas){
  const cw = canvas.width, ch = canvas.height;
  const iw = img.width, ih = img.height;
  const scale = Math.min(cw/iw, ch/ih);
  const w = Math.max(1, Math.floor(iw * scale));
  const h = Math.max(1, Math.floor(ih * scale));
  const x = Math.floor((cw - w)/2);
  const y = Math.floor((ch - h)/2);
  ctx.clearRect(0,0,cw,ch);
  ctx.drawImage(img, x, y, w, h);
  return { x, y, w, h };
}

function redraw(){
  if(!state.img) return;
  const { ctxO, ctxS, canvasO, canvasS } = state;
  const rectO = fitDrawImage(ctxO, state.img, canvasO);
  // simulate by reading only the drawn region for performance
  const imgData = ctxO.getImageData(rectO.x, rectO.y, rectO.w, rectO.h);
  const processed = applySimulationToImageData(imgData, state.type, state.severity);
  ctxS.clearRect(0,0,canvasS.width,canvasS.height);
  ctxS.putImageData(processed, rectO.x, rectO.y);
}

const state = {
  img: null,
  type: 'Deuteranopia',
  severity: 1.0,
  canvasO: null,
  canvasS: null,
  ctxO: null,
  ctxS: null,
};

function setup(){
  const fileInput = document.getElementById('fileInput');
  const typeSelect = document.getElementById('typeSelect');
  const severity = document.getElementById('severity');
  const severityValue = document.getElementById('severityValue');
  const downloadBtn = document.getElementById('downloadBtn');
  state.canvasO = document.getElementById('canvasOriginal');
  state.canvasS = document.getElementById('canvasSim');
  state.ctxO = state.canvasO.getContext('2d');
  state.ctxS = state.canvasS.getContext('2d');

  // allow clicking label to open file chooser
  document.querySelector('label.btn').addEventListener('click',()=> fileInput.click());
  fileInput.addEventListener('change', (e)=>{
    const files = e.target.files;
    if(!files || files.length === 0) return;
    // If multiple files selected, let the multi-select handler render the thumbnail panel
    if(files.length > 1){
      // Hide single preview-only thumb panel if previously shown
      const panel = document.getElementById('thumbPanel');
      if(panel) panel.style.display = 'block';
      return;
    }
    // Single file load into canvases
    const file = files[0];
    const img = new Image();
    img.onload = ()=>{
      state.img = img;
      const maxW = 1280, maxH = 960;
      const scale = Math.min(maxW / img.width, maxH / img.height, 1);
      const w = Math.max(1, Math.floor(img.width * scale));
      const h = Math.max(1, Math.floor(img.height * scale));
      state.canvasO.width = state.canvasS.width = w;
      state.canvasO.height = state.canvasS.height = h;
      downloadBtn.disabled = false;
      // Hide thumbnail panel if visible from a previous multi-select
      const panel = document.getElementById('thumbPanel');
      if(panel) panel.style.display = 'none';
      redraw();
    };
    img.onerror = ()=> alert('Failed to load image.');
    img.src = URL.createObjectURL(file);
  });

  // Build an in-app thumbnail panel from the current folder of the last chosen file.
  // Since browsers can't list folders arbitrarily for security, we emulate this by
  // showing thumbnails for all images selected at once via the file picker (multi-select).
  if (fileInput){
    fileInput.setAttribute('multiple','multiple');
  }
  fileInput.addEventListener('change', (e)=>{
    const files = e.target.files;
    if(!files || files.length <= 1) return; // if user picked multiple, show thumb panel
    const grid = document.getElementById('thumbGrid');
    const panel = document.getElementById('thumbPanel');
    grid.innerHTML = '';
    const list = Array.from(files).filter(f => f.type.startsWith('image/')).slice(0,60);
    for(const f of list){
      const url = URL.createObjectURL(f);
      const img = new Image();
      img.src = url;
      img.style.width = '100%';
      img.style.height = '100px';
      img.style.objectFit = 'cover';
      img.style.borderRadius = '6px';
      img.style.border = '1px solid var(--border)';
      img.title = f.name;
      img.addEventListener('click', ()=>{
        const loaded = new Image();
        loaded.onload = ()=>{
          state.img = loaded;
          const maxW = 1280, maxH = 960;
          const scale = Math.min(maxW / loaded.width, maxH / loaded.height, 1);
          const w = Math.max(1, Math.floor(loaded.width * scale));
          const h = Math.max(1, Math.floor(loaded.height * scale));
          state.canvasO.width = state.canvasS.width = w;
          state.canvasO.height = state.canvasS.height = h;
          redraw();
        };
        loaded.src = url;
      });
      grid.appendChild(img);
    }
    panel.style.display = 'block';
  });

  typeSelect.addEventListener('change', ()=>{
    state.type = typeSelect.value;
    redraw();
  });

  severity.addEventListener('input', ()=>{
    state.severity = parseFloat(severity.value);
    severityValue.textContent = state.severity.toFixed(2);
    redraw();
  });

  downloadBtn.addEventListener('click', ()=>{
    if(!state.img) return;
    // Render fresh simulation to ensure current state
    redraw();
    state.canvasS.toBlob((blob)=>{
      if(!blob){ alert('Export failed.'); return; }
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'simulation.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }, 'image/png');
  });

  // handle window resize—just redraw into current canvas size
  window.addEventListener('resize', ()=> redraw());
}

if (typeof document !== 'undefined' && typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', setup);

// Drag & drop quick preview before selecting
if (typeof document !== 'undefined'){
  const dropHint = document.getElementById('dropHint');
  const prevent = (e)=>{ e.preventDefault(); e.stopPropagation(); };
  ['dragenter','dragover'].forEach(evt=> document.addEventListener(evt, (e)=>{ prevent(e); if(dropHint) dropHint.style.display='flex'; }));
  ['dragleave','drop'].forEach(evt=> document.addEventListener(evt, (e)=>{ prevent(e); if(dropHint) dropHint.style.display='none'; }));
  document.addEventListener('drop', (e)=>{
    const dt = e.dataTransfer; if(!dt || !dt.files || dt.files.length === 0) return;
    const file = dt.files[0];
    if(!file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = ()=>{
      const img = new Image();
      img.onload = ()=>{
        state.img = img;
        const maxW = 1280, maxH = 960;
        const scale = Math.min(maxW / img.width, maxH / img.height, 1);
        const w = Math.max(1, Math.floor(img.width * scale));
        const h = Math.max(1, Math.floor(img.height * scale));
        state.canvasO.width = state.canvasS.width = w;
        state.canvasO.height = state.canvasS.height = h;
        redraw();
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}
}


