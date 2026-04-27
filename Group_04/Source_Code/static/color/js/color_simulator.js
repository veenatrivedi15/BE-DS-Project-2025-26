// Color Blindness Simulator core logic extracted from original app.js
// Wrapped in IIFE to avoid global leakage.
(function(){
  const CB_MATRICES = {
    Protanopia: [ [0.56667, 0.43333, 0.0],[0.55833, 0.44167, 0.0],[0.0, 0.24167, 0.75833] ],
    Deuteranopia: [ [0.625, 0.375, 0.0],[0.7, 0.3, 0.0],[0.0, 0.3, 0.7] ],
    Tritanopia: [ [0.95, 0.05, 0.0],[0.0, 0.43333, 0.56667],[0.0, 0.475, 0.525] ]
  };
  function srgbToLinear(v){ v=Math.min(1,Math.max(0,v)); return v<=0.04045? v/12.92: Math.pow((v+0.055)/1.055,2.4);} 
  function linearToSrgb(v){ v=Math.min(1,Math.max(0,v)); return v<=0.0031308? v*12.92: 1.055*Math.pow(v,1/2.4)-0.055; }
  function applySimulation(imgData,type,severity){ const data=imgData.data; const m=CB_MATRICES[type]; if(!m) return imgData; const s=Math.min(1,Math.max(0,severity)); for(let i=0;i<data.length;i+=4){ let r=data[i]/255,g=data[i+1]/255,b=data[i+2]/255; let rl=srgbToLinear(r),gl=srgbToLinear(g),bl=srgbToLinear(b); const tl_r=rl*m[0][0]+gl*m[0][1]+bl*m[0][2]; const tl_g=rl*m[1][0]+gl*m[1][1]+bl*m[1][2]; const tl_b=rl*m[2][0]+gl*m[2][1]+bl*m[2][2]; const br=(1-s)*rl+s*tl_r; const bg=(1-s)*gl+s*tl_g; const bb=(1-s)*bl+s*tl_b; data[i]=Math.round(255*linearToSrgb(br)); data[i+1]=Math.round(255*linearToSrgb(bg)); data[i+2]=Math.round(255*linearToSrgb(bb)); }
    return imgData; }
  function fitDraw(ctx,img,canvas){ const cw=canvas.width,ch=canvas.height,iw=img.width,ih=img.height; const scale=Math.min(cw/iw,ch/ih); const w=Math.max(1,Math.floor(iw*scale)),h=Math.max(1,Math.floor(ih*scale)); const x=Math.floor((cw-w)/2),y=Math.floor((ch-h)/2); ctx.clearRect(0,0,cw,ch); ctx.drawImage(img,x,y,w,h); return {x,y,w,h}; }
  const state={ img:null,type:'Deuteranopia',severity:1,canvasO:null,canvasS:null,ctxO:null,ctxS:null };
  // Expose for external UI controls (e.g., clear image button)
  if(typeof window!=='undefined'){ window.__CB_SIM_STATE = state; }
  function redraw(){ if(!state.img) return; const {ctxO,ctxS,canvasO,canvasS}=state; const rect=fitDraw(ctxO,state.img,canvasO); const imgData=ctxO.getImageData(rect.x,rect.y,rect.w,rect.h); applySimulation(imgData,state.type,state.severity); ctxS.clearRect(0,0,canvasS.width,canvasS.height); ctxS.putImageData(imgData,rect.x,rect.y);} 
  function setup(){ const fileInput=document.getElementById('fileInput'); const typeSelect=document.getElementById('typeSelect'); const severity=document.getElementById('severity'); const severityValue=document.getElementById('severityValue'); const downloadBtn=document.getElementById('downloadBtn'); state.canvasO=document.getElementById('canvasOriginal'); state.canvasS=document.getElementById('canvasSim'); state.ctxO=state.canvasO.getContext('2d'); state.ctxS=state.canvasS.getContext('2d');
    // Legacy trigger (old label button) guarded to avoid null error after UI refactor
    const legacyLabel=document.querySelector('label.btn'); if(legacyLabel){ legacyLabel.addEventListener('click',()=> fileInput.click()); }
    // If overlay drop zone exists and user clicks empty area, native input already handled by overlay input.
    function loadImage(file){ const img=new Image(); img.onload=()=>{ state.img=img; const maxW=1280,maxH=960; const scale=Math.min(maxW/img.width,maxH/img.height,1); const w=Math.max(1,Math.floor(img.width*scale)); const h=Math.max(1,Math.floor(img.height*scale)); state.canvasO.width=state.canvasS.width=w; state.canvasO.height=state.canvasS.height=h; downloadBtn.disabled=false; redraw(); }; img.onerror=()=> alert('Failed to load image.'); img.src=URL.createObjectURL(file);} fileInput.addEventListener('change', e=>{ const files=e.target.files; if(!files||files.length===0) return; loadImage(files[0]); }); typeSelect.addEventListener('change',()=>{ state.type=typeSelect.value; redraw();}); severity.addEventListener('input',()=>{ state.severity=parseFloat(severity.value); severityValue.textContent=state.severity.toFixed(2); redraw();}); downloadBtn.addEventListener('click',()=>{ if(!state.img) return; redraw(); state.canvasS.toBlob(blob=>{ if(!blob){ alert('Export failed.'); return;} const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='simulation.png'; document.body.appendChild(a); a.click(); a.remove(); },'image/png');}); window.addEventListener('resize',redraw); }
  if(typeof document!=='undefined') document.addEventListener('DOMContentLoaded', setup);
})();