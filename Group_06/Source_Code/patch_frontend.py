import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Comprehensive JS update to dynamically render the JSON payload into the DOM
js_fetch_new = """async function runAnalysis(){
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
      
      // Update Grad-CAM Image
      if(data.gradcam_base64) {
          document.getElementById('dynamic-gradcam').src = 'data:image/png;base64,' + data.gradcam_base64;
      }
      
      // Update the secondary/primary prediction bars dynamically
      const grid = document.querySelector('.results-grid');
      grid.innerHTML = ''; // clear original hardcoded blocks
      
      // Map colors back correctly
      const colorMap = {
          'Lung Cancer': 'var(--red)',
          'Pneumonia': 'var(--blue)',
          'Tuberculosis': 'var(--amber)',
          'Normal': 'var(--green)'
      };
      
      const bgMap = {
          'Lung Cancer': 'var(--red-bg)',
          'Pneumonia': 'var(--blue-bg)',
          'Tuberculosis': 'var(--amber-bg)',
          'Normal': 'var(--green-bg)'
      };
      
      // Rebuild the diagnostic cards
      data.all_predictions.forEach((pred, index) => {
          const isTop = index === 0;
          const color = colorMap[pred.condition];
          const bg = bgMap[pred.condition];
          
          let iconSvg = '';
          if(pred.condition === 'Lung Cancer') iconSvg = '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><circle cx="10" cy="10" r="3"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.9 4.9l1.4 1.4M13.7 13.7l1.4 1.4M4.9 15.1l1.4-1.4M13.7 6.3l1.4-1.4"/></svg>';
          else if(pred.condition === 'Pneumonia') iconSvg = '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><path d="M10 3C6.5 3 4 6 4 9c0 2 1 3.5 2.5 4.5V16h7v-2.5C15 12.5 16 11 16 9c0-3-2.5-6-6-6z"/></svg>';
          else if(pred.condition === 'Tuberculosis') iconSvg = '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><path d="M10 2l2 5h5l-4 3 2 5-5-3-5 3 2-5-4-3h5z"/></svg>';
          else iconSvg = '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><path d="M4 10l4 4 8-8"/></svg>';
          
          grid.innerHTML += `
          <div class="disease-card ${isTop ? 'top-result' : ''}" style="border-top: 3px solid ${color}">
            <div class="d-icon" style="background:${bg}; color:${color}">
              ${iconSvg}
            </div>
            <div class="d-name">${pred.condition}</div>
            <div class="d-conf">${isTop ? 'Primary prediction' : 'Secondary consideration'}</div>
            <div class="d-pct" style="color:${color}">${pred.probability}%</div>
            <div class="progress-bar" style="margin-top:6px">
              <div class="progress-fill" style="width:${pred.probability}%; background:${color}"></div>
            </div>
          </div>`;
      });
      
      // Update Key Findings Text
      const findingsRows = document.querySelectorAll('.analysis-row .a-val');
      if(findingsRows.length > 0) {
          findingsRows[0].innerHTML = data.finding_text;
      }
      
      // Update Report Title
      const reportBanner = document.getElementById('r-primary-disease');
      if (reportBanner) {
         reportBanner.innerHTML = data.top_match + " Diagnosis";
      }
      
      // OVERWRITE SHAP DOM
      const shapPanel = document.getElementById('xai-shap');
      if(shapPanel) {
          // Keep the legend/header the same
          let shapHtml = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div style="font-size:12px;color:var(--ink3);line-height:1.6">SHAP Values computed live indicating contribution to the ${data.top_match} prediction.</div>
          </div>
          <div style="font-size:10px;font-family:var(--mono);color:var(--ink3);margin-bottom:8px;display:flex;gap:8px">
            <span style="width:185px"></span><span style="flex:1;text-align:center">← Reduces Risk &nbsp;|&nbsp; Increases Risk →</span>
          </div>`;
          
          data.shap.forEach(item => {
              const numVal = Math.abs(parseFloat(item.value));
              const w = Math.min(100, Math.max(10, numVal * 100)) + '%';
              const isPos = item.value.includes('+');
              const itemColor = isPos ? 'rgba(192,57,43,.75)' : 'rgba(25,111,61,.75)';
              const txtColor = isPos ? 'var(--red)' : 'var(--green)';
              
              shapHtml += `<div class="shap-row">
                <span class="shap-feat">${item.feature}</span>
                <div class="shap-track">
                  <div class="shap-mid"></div>
                  <div class="${isPos ? 'shap-fill-pos' : 'shap-fill-neg'}" style="width:${w};background:${itemColor}"></div>
                </div>
                <span class="shap-val" style="color:${txtColor}">${item.value}</span>
              </div>`;
          });
          shapPanel.innerHTML = shapHtml;
      }
      
      // OVERWRITE LIME DOM
      const limePanel = document.getElementById('xai-lime');
      if(limePanel) {
          limePanel.innerHTML = `<div style="font-size:12px;color:var(--ink3);margin-bottom:14px;line-height:1.6">LIME Perturbation calculated specific to this uploaded image.</div>
          <div class="lime-block">
            <div class="lime-rule">${data.lime.rule}</div>
            <div class="lime-weight">
              <div class="lime-w-track">
                <div class="lime-w-fill" style="width:90%;background:rgba(192,57,43,.75)"></div>
              </div>
              <span class="lime-w-val" style="color:var(--red)">${data.lime.weight}</span>
            </div>
            <div class="lime-verdict">${data.lime.desc}</div>
          </div>`;
      }
      
      setTimeout(()=>{
        document.getElementById('loading-overlay').classList.remove('show');
        document.getElementById('predict-results').style.display='block';
        showToast(`Analysis complete — ${data.top_match} detected with ${data.confidence}% confidence`, 'success');
      }, 1000); 
      
  } catch(e) {
      document.getElementById('loading-overlay').classList.remove('show');
      showToast(e.message, 'error');
  }
}"""

# Use regex to find and replace the current runAnalysis function cleanly
# This handles the previous patches easily.
pattern = re.compile(r'async function runAnalysis\(\).*?\}\s*\}', re.DOTALL)
if pattern.search(html):
    html = pattern.sub(js_fetch_new, html)
else:
    # If it was the original one:
    pattern2 = re.compile(r'function runAnalysis\(\)\{.*?nextStep\(\);\n\}', re.DOTALL)
    html = pattern2.sub(js_fetch_new, html)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Sophisticated frontend DOM patching complete")
