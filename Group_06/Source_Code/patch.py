import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace Grad-CAM static SVG with dynamic img tag
gradcam_svg = """<svg viewBox="0 0 200 180">
                <rect width="200" height="180" fill="#060c18"/>
                <ellipse cx="100" cy="93" rx="74" ry="70" fill="#0a1828" stroke="#122038" stroke-width="1"/>
                <ellipse cx="66" cy="93" rx="22" ry="32" fill="#142844"/>
                <ellipse cx="134" cy="93" rx="22" ry="32" fill="#142844"/>
                <path d="M100 45 Q101 60 100 76 Q99 90 100 112" fill="none" stroke="#1e3a60" stroke-width="5" stroke-linecap="round"/>
                <!-- heatmap rings centered on nodule -->
                <circle cx="127" cy="68" r="38" fill="rgba(26,82,118,.18)"/>
                <circle cx="127" cy="68" r="28" fill="rgba(184,134,11,.22)"/>
                <circle cx="127" cy="68" r="20" fill="rgba(245,158,11,.35)"/>
                <circle cx="127" cy="68" r="14" fill="rgba(192,57,43,.55)"/>
                <circle cx="127" cy="68" r="8" fill="rgba(231,76,60,.8)"/>
                <circle cx="127" cy="68" r="4" fill="rgba(255,200,200,.9)"/>
                <!-- crosshair -->
                <line x1="112" y1="68" x2="118" y2="68" stroke="white" stroke-width=".8" opacity=".6"/>
                <line x1="136" y1="68" x2="142" y2="68" stroke="white" stroke-width=".8" opacity=".6"/>
                <line x1="127" y1="53" x2="127" y2="59" stroke="white" stroke-width=".8" opacity=".6"/>
                <line x1="127" y1="77" x2="127" y2="83" stroke="white" stroke-width=".8" opacity=".6"/>
                <text x="100" y="172" fill="#1a4a6a" font-size="7" font-family="monospace" text-anchor="middle">Grad-CAM · Cancer Class</text>
              </svg>"""

img_tag = """<img id="dynamic-gradcam" src="" style="width:100%; height:100%; object-fit: cover;" alt="Loading Grad-CAM...">"""
html = html.replace(gradcam_svg, img_tag)

# Replace the runAnalysis javascript function to call the backend instead
js_original = """function runAnalysis(){
  goStep(2);
  document.getElementById('loading-overlay').classList.add('show');
  document.getElementById('predict-results').style.display='none';
  const steps2=['ls1','ls2','ls3','ls4','ls5','ls6'];
  let i=0;
  function nextStep(){
    if(i>0) {
      const prev=document.getElementById(steps2[i-1]);
      prev.classList.remove('active'); prev.classList.add('done');
      prev.querySelector('.ls-check').innerHTML='<svg class="ls-check-svg" viewBox="0 0 8 8"><path d="M1 4l2 2 4-4"/></svg>';
    }
    if(i<steps2.length){
      document.getElementById(steps2[i]).classList.add('active');
      i++;
      setTimeout(nextStep,750);
    } else {
      setTimeout(()=>{
        document.getElementById('loading-overlay').classList.remove('show');
        document.getElementById('predict-results').style.display='block';
        showToast('Analysis complete — Lung Cancer detected with 87.4% confidence','success');
      },400);
    }
  }
  nextStep();
}"""

js_fetch = """async function runAnalysis(){
  const fileInput = document.querySelector('#upload-primary input');
  if(!fileInput.files[0]) {
      showToast('Please upload a primary scan', 'error');
      return;
  }
  
  goStep(2);
  document.getElementById('loading-overlay').classList.add('show');
  document.getElementById('predict-results').style.display='none';
  
  // Prepare Form Data
  const formData = new FormData();
  formData.append('scan', fileInput.files[0]);
  formData.append('age', document.getElementById('ehr-age').value);
  formData.append('gender', document.getElementById('ehr-gender').value);
  formData.append('symptoms', getSelectedSymptoms());
  formData.append('smoke', document.getElementById('ehr-smoke').value);
  
  try {
      const response = await fetch('/predict', {
          method: 'POST',
          body: formData
      });
      
      const data = await response.json();
      
      if(data.error) throw new Error(data.error);
      
      // Update DOM with Backend Data
      if(data.gradcam_base64) {
          document.getElementById('dynamic-gradcam').src = 'data:image/png;base64,' + data.gradcam_base64;
      }
      
      // Update confidence UI dynamically
      document.querySelector('.d-pct').textContent = data.confidence + '%';
      document.querySelector('.progress-fill').style.width = data.confidence + '%';
      document.querySelector('.disease-card.cancer .d-name').textContent = data.top_match;
      
      setTimeout(()=>{
        document.getElementById('loading-overlay').classList.remove('show');
        document.getElementById('predict-results').style.display='block';
        showToast(`Analysis complete — ${data.top_match} detected with ${data.confidence}% confidence`, 'success');
      }, 1500); // Small delay to simulate steps for visual polish
      
  } catch(e) {
      document.getElementById('loading-overlay').classList.remove('show');
      showToast(e.message, 'error');
  }
}"""
if js_original in html:
    html = html.replace(js_original, js_fetch)
else:
    print("Warning: could not find JS original text")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Patch complete")
