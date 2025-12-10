from flask import Flask, render_template_string, request, send_file, jsonify
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw, ImageChops
import io
import base64
import os
from werkzeug.utils import secure_filename
import zipfile

app = Flask(_name_)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drawing Comparison Tool | Hackathon 2024</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
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
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 8px 20px;
            border-radius: 20px;
            margin-top: 15px;
            font-weight: bold;
        }
        .content { padding: 40px; }
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
        .upload-icon { font-size: 4em; margin-bottom: 20px; }
        input[type="file"] { display: none; }
        .settings {
            background: #f8f9ff;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        .settings h3 { color: #667eea; margin-bottom: 20px; }
        .setting-group { margin-bottom: 20px; }
        .setting-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
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
        .results { display: none; }
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
        }
        .download-btn:hover { background: #45a049; }
        @media (max-width: 768px) {
            .upload-section, .stats, .comparison-images { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Engineering Drawing Comparison</h1>
            <p>Simplified Version - Works Everywhere!</p>
            <div class="badge">Hackathon 2024</div>
        </div>
        
        <div class="content">
            <div class="upload-section">
                <div class="upload-box" id="upload1" onclick="document.getElementById('file1').click()">
                    <div class="upload-icon">📄</div>
                    <h3>Original Drawing</h3>
                    <p>Click to upload</p>
                    <p id="file1-name" style="margin-top: 10px; color: #667eea; font-weight: bold;"></p>
                </div>
                
                <div class="upload-box" id="upload2" onclick="document.getElementById('file2').click()">
                    <div class="upload-icon">📄</div>
                    <h3>Revised Drawing</h3>
                    <p>Click to upload</p>
                    <p id="file2-name" style="margin-top: 10px; color: #667eea; font-weight: bold;"></p>
                </div>
            </div>
            
            <input type="file" id="file1" accept=".pdf" onchange="handleFileSelect(1)">
            <input type="file" id="file2" accept=".pdf" onchange="handleFileSelect(2)">
            
            <div class="settings">
                <h3>⚙️ Comparison Settings</h3>
                <div class="setting-group">
                    <label>Sensitivity (Higher = Less Sensitive)</label>
                    <div class="slider-container">
                        <input type="range" id="threshold" min="20" max="100" value="50" 
                               oninput="document.getElementById('threshold-value').textContent = this.value">
                        <span class="slider-value" id="threshold-value">50</span>
                    </div>
                </div>
            </div>
            
            <button class="compare-btn" id="compareBtn" onclick="compareDrawings()" disabled>
                🔍 Compare Drawings
            </button>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <h3>Processing...</h3>
            </div>
            
            <div class="results" id="results">
                <h2 style="margin: 40px 0 30px; color: #667eea; text-align: center;">📊 Results</h2>
                <div class="stats">
                    <div class="stat-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                        <div>Additions</div>
                        <div class="stat-value" id="additions">0</div>
                        <div>pixels</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);">
                        <div>Deletions</div>
                        <div class="stat-value" id="deletions">0</div>
                        <div>pixels</div>
                    </div>
                    <div class="stat-card">
                        <div>Total Changes</div>
                        <div class="stat-value" id="changes">0</div>
                        <div>%</div>
                    </div>
                </div>
                
                <div class="comparison-images" id="images"></div>
                <button class="download-btn" onclick="downloadResults()">⬇️ Download Results</button>
            </div>
        </div>
    </div>
    
    <script>
        let file1 = null, file2 = null;
        
        function handleFileSelect(num) {
            const file = document.getElementById('file' + num).files[0];
            if (file) {
                if (num === 1) file1 = file; else file2 = file;
                document.getElementById('file' + num + '-name').textContent = file.name;
                document.getElementById('upload' + num).classList.add('active');
                if (file1 && file2) document.getElementById('compareBtn').disabled = false;
            }
        }
        
        async function compareDrawings() {
            if (!file1 || !file2) return;
            
            document.getElementById('compareBtn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            const formData = new FormData();
            formData.append('file1', file1);
            formData.append('file2', file2);
            formData.append('threshold', document.getElementById('threshold').value);
            
            try {
                const response = await fetch('/compare', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.error) { alert('Error: ' + data.error); return; }
                displayResults(data);
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                document.getElementById('compareBtn').style.display = 'block';
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        function displayResults(data) {
            document.getElementById('additions').textContent = data.additions.toLocaleString();
            document.getElementById('deletions').textContent = data.deletions.toLocaleString();
            document.getElementById('changes').textContent = data.change_percent + '%';
            
            document.getElementById('images').innerHTML = `
                <div class="image-card">
                    <h4>Original</h4>
                    <img src="data:image/png;base64,${data.original}" alt="Original">
                </div>
                <div class="image-card">
                    <h4>Revised</h4>
                    <img src="data:image/png;base64,${data.revised}" alt="Revised">
                </div>
                <div class="image-card">
                    <h4>Differences</h4>
                    <img src="data:image/png;base64,${data.comparison}" alt="Comparison">
                </div>
            `;
            
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

def compare_pdfs_simple(file1_path, file2_path, threshold=50):
    """Simple comparison without OpenCV"""
    doc1 = fitz.open(file1_path)
    doc2 = fitz.open(file2_path)
    
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    
    pix1 = doc1[0].get_pixmap(matrix=mat)
    pix2 = doc2[0].get_pixmap(matrix=mat)
    
    # Convert to PIL
    img1 = Image.frombytes("RGB", [pix1.width, pix1.height], pix1.samples)
    img2 = Image.frombytes("RGB", [pix2.width, pix2.height], pix2.samples)
    
    # Make same size
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)
    
    # Simple difference
    diff = ImageChops.difference(img1, img2)
    
    # Convert to grayscale for analysis
    gray_diff = diff.convert('L')
    pixels = list(gray_diff.getdata())
    
    # Count changed pixels
    changed = sum(1 for p in pixels if p > threshold)
    total = len(pixels)
    change_percent = round((changed / total) * 100, 2)
    
    # Create colored difference image
    result = img2.copy()
    result_pixels = result.load()
    diff_pixels = gray_diff.load()
    
    width, height = img2.size
    additions = 0
    deletions = 0
    
    for y in range(height):
        for x in range(width):
            if diff_pixels[x, y] > threshold:
                # Simple heuristic: lighter = deletion, darker = addition
                if sum(img2.getpixel((x, y))) > sum(img1.getpixel((x, y))):
                    result_pixels[x, y] = (0, 255, 0)  # Green
                    additions += 1
                else:
                    result_pixels[x, y] = (255, 0, 0)  # Red
                    deletions += 1
    
    doc1.close()
    doc2.close()
    
    return {
        'original': img1,
        'revised': img2,
        'comparison': result,
        'additions': additions,
        'deletions': deletions,
        'change_percent': change_percent
    }

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/compare', methods=['POST'])
def compare():
    try:
        file1 = request.files['file1']
        file2 = request.files['file2']
        threshold = int(request.form.get('threshold', 50))
        
        file1_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file1.filename))
        file2_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file2.filename))
        
        file1.save(file1_path)
        file2.save(file2_path)
        
        results = compare_pdfs_simple(file1_path, file2_path, threshold)
        
        def img_to_base64(img):
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        app.config['LAST_RESULTS'] = results
        
        return jsonify({
            'original': img_to_base64(results['original']),
            'revised': img_to_base64(results['revised']),
            'comparison': img_to_base64(results['comparison']),
            'additions': results['additions'],
            'deletions': results['deletions'],
            'change_percent': results['change_percent']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download():
    results = app.config.get('LAST_RESULTS')
    if not results:
        return "No results", 404
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for name, img in [('original', results['original']), 
                          ('revised', results['revised']), 
                          ('comparison', results['comparison'])]:
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            zf.writestr(f'{name}.png', img_buffer.getvalue())
    
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', 
                     as_attachment=True, download_name='results.zip')

if _name_ == '_main_':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
