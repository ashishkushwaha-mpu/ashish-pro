from flask import Flask, request, render_template_string, send_file, jsonify
import yt_dlp
import os
import threading

app = Flask(__name__)

download_progress = {}

def progress_hook(d):
    """ Track download progress and store it in a dictionary """
    if d['status'] == 'downloading':
        video_id = d['info_dict'].get('id', 'unknown')
        download_progress[video_id] = round((d['downloaded_bytes'] / d['total_bytes']) * 100)

@app.route("/progress/<video_id>")
def progress(video_id):
    """ API to fetch the progress of a download """
    return jsonify({"progress": download_progress.get(video_id, 0)})

@app.route("/", methods=["GET", "POST"])
def home():
    file_url = None
    message = None
    video_id = None

    if request.method == "POST":
        url = request.form.get("url")
        format_choice = request.form.get("format")

        try:
            ydl_opts = {
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'progress_hooks': [progress_hook]
            }

            if format_choice == "mp3":
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegAudioConvertor',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            elif format_choice == "mp4_1080p":
                ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
            elif format_choice == "mp4_720p":
                ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
            else:
                ydl_opts['format'] = 'best'

            def download_video():
                """ Download video/audio in a separate thread """
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(url, download=True)
                    nonlocal video_id
                    video_id = result.get("id")
                    file_name = ydl.prepare_filename(result)
                    download_progress[video_id] = 100  # Mark as complete
                    return file_name
            
            thread = threading.Thread(target=download_video)
            thread.start()

            return render_template_string(template, message="Download in progress!", video_id=video_id)

        except Exception as e:
            message = f"Error: {str(e)}"
            return render_template_string(template, message=message)

    return render_template_string(template, message=message)

@app.route('/download/<filename>')
def download_file(filename):
    """ Serve the downloaded file """
    file_path = os.path.join("downloads", filename)
    return send_file(file_path, as_attachment=True)

# HTML template with logos for YouTube, Instagram, and Facebook
template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Downloader (YouTube, Instagram, Facebook)</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            background-color: #f4f4f4;
            padding: 20px;
        }
        .logo-container {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
        }
        .logo-container img {
            width: 50px;
            height: 50px;
        }
        form {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
            width: 400px;
            margin: 0 auto;
        }
        input, select, button {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
        }
        button:hover {
            background: #45a049;
        }
        .progress-bar {
            width: 100%;
            background: #ddd;
            height: 20px;
            margin-top: 10px;
            border-radius: 5px;
            display: none;
        }
        .progress-bar-inner {
            height: 100%;
            width: 0;
            background: #4CAF50;
            border-radius: 5px;
        }
    </style>
    <script>
        function checkProgress(videoId) {
            if (!videoId) return;
            fetch('/progress/' + videoId)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('progress-bar').style.display = 'block';
                    document.getElementById('progress-bar-inner').style.width = data.progress + '%';
                    if (data.progress < 100) {
                        setTimeout(() => checkProgress(videoId), 1000);
                    } else {
                        document.getElementById('download-link').style.display = 'block';
                    }
                });
        }
    </script>
</head>
<body onload="checkProgress('{{ video_id }}')">
    <h1>Download Videos from YouTube, Instagram & Facebook</h1>

    <div class="logo-container">
        <img src="https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg" alt="YouTube">
        <img src="https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png" alt="Instagram">
        <img src="https://upload.wikimedia.org/wikipedia/commons/5/51/Facebook_f_logo_%282019%29.svg" alt="Facebook">
    </div>

    <form action="/" method="POST">
        <input type="text" name="url" placeholder="Enter video URL (YouTube, Instagram, Facebook)" required>
        
        <label for="format">Select Download Type:</label>
        <select name="format" id="format">
            <option value="mp4_best">Video (MP4) - Best Quality</option>
            <option value="mp4_1080p">Video (MP4) - 1080p</option>
            <option value="mp4_720p">Video (MP4) - 720p</option>
            <option value="mp3">Audio (MP3)</option>
        </select>

        <button type="submit">Download</button>
    </form>

    {% if message %}
        <p>{{ message }}</p>
    {% endif %}
    
    <div id="progress-bar" class="progress-bar">
        <div id="progress-bar-inner" class="progress-bar-inner"></div>
    </div>

    <div id="download-link" style="display: none;">
        <p>Click <a href="{{ file_url }}" download>here</a> to download the file.</p>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run(debug=True)
