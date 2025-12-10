from flask import Flask, render_template_string, request, send_file, jsonify
import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image
import io
import base64
import os
from werkzeug.utils import secure_filename
import zipfile
from datetime import datetime

app = Flask(_name_)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ========== HTML TEMPLATE ==========
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Engineering Drawing Comparison Tool | Hackathon 2024</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 8px 20px;
            border-radius: 20px;
            margin-top: 15px;
            font-weight: bold;
        }
        
        .content {
            padding: 40px;
        }
        
        .upload-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .upload-box {
            border: 3px dashed #667eea;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #f8f9ff;
        }
        
        .upload-box:hover {
            background: #eef1ff;
            border-color: #764ba2;
            transform: translateY(-5px);
        }
        
        .upload-box.active {
            background: #e8f5e9;
            border-color: #4caf50;
        }
        
        .upload-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        
        input[type="file"] {
            display: none;
        }
        
        .settings {
            background: #f8f9ff;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        
        .settings h3 {
            color: #667eea;
            margin-bottom: 20px;
        }
        
        .setting-group {
            margin-bottom: 20px;
        }
        
        .setting-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        .slider-container {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        input[type="range"] {
            flex: 1;
            height: 8px;
            border-radius: 5px;
            background: #ddd;
            outline: none;
        }
        
        .slider-value {
            min-width: 50px;
            text-align: right;
            font-weight: bold;
            color: #667eea;
        }
        
        .compare-btn {
            width: 100%;
            padding: 20px;
            font-size: 1.3em;
            font-weight: bold;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        
        .compare-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
        }
        
        .compare-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .results {
            display: none;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .stat-label {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .comparison-images {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .image-card {
            background: #f8f9ff;
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .image-card h4 {
            color: #667eea;
            margin-bottom: 15px;
            text-align: center;
        }
        
        .image-card img {
            width: 100%;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }
        
        .download-btn {
            width: 100%;
            padding: 15px;
            font-size: 1.1em;
            font-weight: bold;
            color: white;
            background: #4caf50;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .download-btn:hover {
            background: #45a049;
            transform: translateY(-2px);
        }
        
        .footer {
            background: #f8f9ff;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .upload-section { grid-template-columns: 1fr; }
            .stats { grid-template-columns: 1fr; }
            .comparison-images { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Engineering Drawing Comparison Tool</h1>
            <p>AI-Powered PDF Comparison with Auto-Alignment</p>
            <div class="badge">Hackathon 2024 Project</div>
        </div>
        
        <div class="content">
            <div class="upload-section">
                <div class="upload-box" id="upload1" onclick="document.getElementById('file1').click()">
                    <div class="upload-icon">📄</div>
                    <h3>Original Drawing</h3>
                    <p>Click to upload older version</p>
                    <p id="file1-name" style="margin-top: 10px; color: #667eea; font-weight: bold;"></p>
                </div>
                
                <div class="upload-box" id="upload2" onclick="document.getElementById('file2').click()">
                    <div class="upload-icon">📄</div>
                    <h3>Revised Drawing</h3>
                    <p>Click to upload newer version</p>
                    <p id="file2-name" style="margin-top: 10px; color: #667eea; font-weight: bold;"></p>
                </div>
            </div>
            
            <input type="file" id="file1" accept=".pdf" onchange="handleFileSelect(1)">
            <input type="file" id="file2" accept=".pdf" onchange="handleFileSelect(2)">
            
            <div class="settings">
                <h3>⚙️ Comparison Settings</h3>
                
                <div class="setting-group">
                    <label>Sensitivity Threshold (Higher = Less Sensitive)</label>
                    <div class="slider-container">
                        <input type="range" id="threshold" min="20" max="80" value="40" 
                               oninput="updateSlider('threshold', this.value)">
                        <span class="slider-value" id="threshold-value">40</span>
                    </div>
                </div>
                
                <div class="setting-group">
                    <label>Blur Amount (Noise Reduction)</label>
                    <div class="slider-container">
                        <input type="range" id="blur" min="3" max="11" step="2" value="7" 
                               oninput="updateSlider('blur', this.value)">
                        <span class="slider-value" id="blur-value">7</span>
                    </div>
                </div>
                
                <div class="setting-group">
                    <label>Minimum Change Area (pixels)</label>
                    <div class="slider-container">
                        <input type="range" id="minarea" min="100" max="2000" step="100" value="500" 
                               oninput="updateSlider('minarea', this.value)">
                        <span class="slider-value" id="minarea-value">500</span>
                    </div>
                </div>
            </div>
            
            <button class="compare-btn" id="compareBtn" onclick="compareDrawings()" disabled>
                🔍 Compare Drawings
            </button>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <h3>Processing your drawings...</h3>
                <p>This may take 10-30 seconds depending on file size</p>
            </div>
            
            <div class="results" id="results">
                <h2 style="margin: 40px 0 30px; color: #667eea; text-align: center;">📊 Comparison Results</h2>
                
                <div class="stats">
                    <div class="stat-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                        <div class="stat-label">Additions</div>
                        <div class="stat-value" id="additions">0</div>
                        <div class="stat-label">pixels</div>
                    </div>
                    
                    <div class="stat-card" style="background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);">
                        <div class="stat-label">Deletions</div>
                        <div class="stat-value" id="deletions">0</div>
                        <div class="stat-label">pixels</div>
                    </div>
                    
                    <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <div class="stat-label">Total Changes</div>
                        <div class="stat-value" id="changes">0</div>
                        <div class="stat-label">regions</div>
                    </div>
                </div>
                
                <div class="comparison-images" id="images">
                    <!-- Images will be inserted here -->
                </div>
                
                <button class="download-btn" onclick="downloadResults()">
                    ⬇️ Download All Results (ZIP)
                </button>
            </div>
        </div>
        
        <div class="footer">
            <p>Built for Hackathon 2024 | Using AI-powered image alignment and OpenCV</p>
            <p style="margin-top: 10px;">Handles position shifts, rotation, and scaling automatically</p>
        </div>
    </div>
    
    <script>
        let file1 = null;
        let file2 = null;
        
        function handleFileSelect(num) {
            const fileInput = document.getElementById('file' + num);
            const file = fileInput.files[0];
            
            if (file) {
                if (num === 1) file1 = file;
                else file2 = file;
                
                document.getElementById('file' + num + '-name').textContent = file.name;
                document.getElementById('upload' + num).classList.add('active');
                
                if (file1 && file2) {
                    document.getElementById('compareBtn').disabled = false;
                }
            }
        }
        
        function updateSlider(id, value) {
            document.getElementById(id + '-value').textContent = value;
        }
        
        async function compareDrawings() {
            if (!file1 || !file2) {
                alert('Please upload both PDF files');
                return;
            }
            
            // Show loading
            document.getElementById('compareBtn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            // Prepare form data
            const formData = new FormData();
            formData.append('file1', file1);
            formData.append('file2', file2);
            formData.append('threshold', document.getElementById('threshold').value);
            formData.append('blur', document.getElementById('blur').value);
            formData.append('minarea', document.getElementById('minarea').value);
            
            try {
                const response = await fetch('/compare', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                // Display results
                displayResults(data);
                
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                document.getElementById('compareBtn').style.display = 'block';
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        function displayResults(data) {
            // Update stats
            document.getElementById('additions').textContent = data.additions.toLocaleString();
            document.getElementById('deletions').textContent = data.deletions.toLocaleString();
            document.getElementById('changes').textContent = data.changes;
            
            // Display images
            const imagesDiv = document.getElementById('images');
            imagesDiv.innerHTML = `
                <div class="image-card">
                    <h4>Original Drawing</h4>
                    <img src="data:image/png;base64,${data.original}" alt="Original">
                </div>
                <div class="image-card">
                    <h4>Revised Drawing</h4>
                    <img src="data:image/png;base64,${data.revised}" alt="Revised">
                </div>
                <div class="image-card">
                    <h4>Differences Highlighted</h4>
                    <img src="data:image/png;base64,${data.comparison}" alt="Comparison">
                </div>
            `;
            
            // Show results
            document.getElementById('results').style.display = 'block';
            document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
        }
        
        async function downloadResults() {
            const response = await fetch('/download');
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'comparison_results.zip';
            a.click();
        }
    </script>
</body>
</html>
"""

# ========== COMPARISON LOGIC ==========
def align_images_orb(img1, img2):
    """Align images using ORB"""
    gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)
    
    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)
    
    if des1 is None or des2 is None:
        return img2
    
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(matcher.match(des1, des2), key=lambda x: x.distance)[:500]
    
    if len(matches) < 10:
        return img2
    
    pts1 = np.float32([kp1[m.queryIdx].pt for m in matches])
    pts2 = np.float32([kp2[m.trainIdx].pt for m in matches])
    
    h, _ = cv2.findHomography(pts2, pts1, cv2.RANSAC, 5.0)
    
    if h is None:
        return img2
    
    return cv2.warpPerspective(img2, h, (img1.shape[1], img1.shape[0]))

def compare_pdfs(file1_path, file2_path, threshold=40, blur=7, min_area=500):
    """Compare two PDFs"""
    doc1 = fitz.open(file1_path)
    doc2 = fitz.open(file2_path)
    
    # Get first page only for demo
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    
    pix1 = doc1[0].get_pixmap(matrix=mat)
    pix2 = doc2[0].get_pixmap(matrix=mat)
    
    img1 = np.frombuffer(pix1.samples, dtype=np.uint8).reshape(pix1.height, pix1.width, 3)
    img2 = np.frombuffer(pix2.samples, dtype=np.uint8).reshape(pix2.height, pix2.width, 3)
    
    # Align
    img2_aligned = align_images_orb(img1, img2)
    
    # Convert to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(img2_aligned, cv2.COLOR_RGB2GRAY)
    
    # Preprocessing
    kernel = np.ones((3,3), np.uint8)
    gray1 = cv2.GaussianBlur(gray1, (blur, blur), 0)
    gray2 = cv2.GaussianBlur(gray2, (blur, blur), 0)
    
    # Difference
    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered = [c for c in contours if cv2.contourArea(c) > min_area]
    
    # Create result
    result = img2_aligned.copy()
    mask_add = np.zeros_like(gray1)
    mask_del = np.zeros_like(gray1)
    
    for cnt in filtered:
        x, y, w, h = cv2.boundingRect(cnt)
        roi1 = gray1[y:y+h, x:x+w]
        roi2 = gray2[y:y+h, x:x+w]
        
        if roi1.size == 0 or roi2.size == 0:
            continue
        
        if np.mean(roi2) < np.mean(roi1) - 10:
            cv2.drawContours(mask_add, [cnt], -1, 255, -1)
        elif np.mean(roi1) < np.mean(roi2) - 10:
            cv2.drawContours(mask_del, [cnt], -1, 255, -1)
    
    # Apply colors
    overlay = result.copy()
    overlay[mask_add > 0] = [0, 255, 0]
    overlay[mask_del > 0] = [255, 0, 0]
    result = cv2.addWeighted(result, 0.5, overlay, 0.5, 0)
    
    # Draw boxes
    for cnt in filtered:
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(result, (x, y), (x+w, y+h), (255, 255, 0), 2)
    
    doc1.close()
    doc2.close()
    
    return {
        'original': img1,
        'revised': img2_aligned,
        'comparison': result,
        'additions': int(np.sum(mask_add > 0)),
        'deletions': int(np.sum(mask_del > 0)),
        'changes': len(filtered)
    }

# ========== ROUTES ==========
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/compare', methods=['POST'])
def compare():
    try:
        file1 = request.files['file1']
        file2 = request.files['file2']
        threshold = int(request.form.get('threshold', 40))
        blur = int(request.form.get('blur', 7))
        minarea = int(request.form.get('minarea', 500))
        
        # Save files
        file1_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file1.filename))
        file2_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file2.filename))
        
        file1.save(file1_path)
        file2.save(file2_path)
        
        # Compare
        results = compare_pdfs(file1_path, file2_path, threshold, blur, minarea)
        
        # Convert images to base64
        def img_to_base64(img):
            _, buffer = cv2.imencode('.png', cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            return base64.b64encode(buffer).decode('utf-8')
        
        # Store for download
        app.config['LAST_RESULTS'] = results
        
        return jsonify({
            'original': img_to_base64(results['original']),
            'revised': img_to_base64(results['revised']),
            'comparison': img_to_base64(results['comparison']),
            'additions': results['additions'],
            'deletions': results['deletions'],
            'changes': results['changes']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download():
    results = app.config.get('LAST_RESULTS')
    if not results:
        return "No results available", 404
    
    # Create ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for name, img in [('original', results['original']), 
                          ('revised', results['revised']), 
                          ('comparison', results['comparison'])]:
            _, buffer = cv2.imencode('.png', cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            zf.writestr(f'{name}.png', buffer.tobytes())
    
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', 
                     as_attachment=True, download_name='comparison_results.zip')

if _name_ == '_main_':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)