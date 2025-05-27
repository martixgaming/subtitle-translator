from flask import Flask, render_template, request, jsonify, send_file
import os
import subprocess
import threading
import time
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from googletrans import Translator
import whisper
import srt
import webvtt

progress = 0

app = Flask(__name__)
translator = Translator()

# Load Whisper model once
model = whisper.load_model("base")

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    file = request.files.get('file')

    if not file:
        return jsonify({"error": "No file received"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    subtitle_path = os.path.join(UPLOAD_FOLDER, os.path.splitext(file.filename)[0] + ".vtt")

    file.save(file_path)

    if not os.path.exists(subtitle_path):
        subtitle_path = extract_subtitles(file_path)
        if not subtitle_path:
            return jsonify({"error": "Failed to generate subtitles"}), 500

    return jsonify({
        "message": "File uploaded successfully",
        "video_path": file.filename,
        "subtitle_path": os.path.basename(subtitle_path)
    })

@app.route('/get_video', methods=['GET'])
def get_video():
    video_path = request.args.get('video_path')
    full_video_path = os.path.join(UPLOAD_FOLDER, video_path)

    if not os.path.exists(full_video_path):
        return jsonify({"error": "Video not found"}), 404
    return send_file(full_video_path)

@app.route('/translate', methods=['POST'])
def translate_subtitles():
    global progress
    progress = 0

    video_file_path = request.json.get('video_file_path')
    target_language = request.json.get('target_language')

    if not video_file_path or not target_language:
        return jsonify({"error": "No video file path or target language provided."}), 400

    full_video_path = os.path.join(UPLOAD_FOLDER, video_file_path)
    subtitle_path = extract_subtitles(full_video_path)

    if not subtitle_path:
        return jsonify({"error": "No subtitles found in video."}), 400

    srt_path = subtitle_path.replace('.vtt', '.srt')
    if not os.path.exists(srt_path):
        return jsonify({"error": "Original SRT subtitle file not found."}), 404

    with open(srt_path, 'r', encoding='utf-8') as f:
        subs = list(srt.parse(f.read()))

    def translate_and_save_subtitles():
        global progress
        translated_subs = []

        for idx, sub in enumerate(subs):
            try:
                translated_text = translator.translate(sub.content, src="en", dest=target_language).text
            except Exception as e:
                print(f"Translation error at subtitle {idx}: {e}")
                translated_text = sub.content
            translated_subs.append(
                srt.Subtitle(index=sub.index, start=sub.start, end=sub.end, content=translated_text)
            )
            progress = int((idx / len(subs)) * 100)
            time.sleep(0.1)

        translated_srt = srt.compose(translated_subs)
        translated_srt_path = os.path.join(UPLOAD_FOLDER, "translated_subtitles.srt")
        with open(translated_srt_path, "w", encoding="utf-8") as f:
            f.write(translated_srt)

        translated_vtt_path = os.path.join(UPLOAD_FOLDER, "translated_subtitles.vtt")
        webvtt.from_srt(translated_srt_path).save(translated_vtt_path)

        video_with_subtitles_path = os.path.join(UPLOAD_FOLDER, f"Test_with_{target_language}_subtitles.mp4")
        success = add_subtitles_to_video(full_video_path, translated_vtt_path, video_with_subtitles_path)

        if success:
            progress = 100
        else:
            progress = 0

    threading.Thread(target=translate_and_save_subtitles, daemon=True).start()

    return jsonify({"message": "Translation started. Check progress bar."})

@app.route('/done', methods=['GET'])
def translation_done():
    global progress
    if progress >= 100:
        return jsonify({"message": "Translation is completed. You can download now."})
    else:
        return jsonify({"message": "Translation in progress."})

@app.route('/download_video_with_subtitles', methods=['GET'])
def download_video_with_subtitles():
    target_language = request.args.get('lang', 'fa')
    video_path = os.path.join(UPLOAD_FOLDER, f"Test_with_{target_language}_subtitles.mp4")

    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=True)
    else:
        return jsonify({"error": "Translated video file not found."}), 404

@app.route('/download_translated_subtitles', methods=['GET'])
def download_translated_subtitles():
    path_to_subtitles_file = os.path.join(UPLOAD_FOLDER, "translated_subtitles.vtt")

    if os.path.exists(path_to_subtitles_file):
        return send_file(path_to_subtitles_file, as_attachment=True)
    else:
        return jsonify({"error": "Translated subtitles file not found."}), 404

@app.route('/get_subtitles')
def get_subtitles():
    video_path = request.args.get('video_path')
    if not video_path:
        return jsonify({"error": "Video path not provided"}), 400

    subtitle_path = os.path.join(UPLOAD_FOLDER, os.path.splitext(video_path)[0] + ".vtt")

    if os.path.exists(subtitle_path):
        return send_file(subtitle_path, as_attachment=True)
    else:
        return jsonify({"error": "Subtitles file not found."}), 404

@app.route('/progress', methods=['GET'])
def get_progress():
    global progress
    return jsonify({"progress": progress})

def extract_subtitles(video_path):
    try:
        result = model.transcribe(video_path)
        srt_path = video_path.rsplit('.', 1)[0] + ".srt"

        subtitles = []
        for i, segment in enumerate(result["segments"], 1):
            start = srt.timedelta(seconds=segment["start"])
            end = srt.timedelta(seconds=segment["end"])
            content = segment["text"].strip()

            subtitle = srt.Subtitle(index=i, start=start, end=end, content=content)
            subtitles.append(subtitle)

        srt_content = srt.compose(subtitles)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        vtt_path = video_path.rsplit('.', 1)[0] + ".vtt"
        webvtt.from_srt(srt_path).save(vtt_path)

        return vtt_path
    except Exception as e:
        print(f"Error extracting subtitles: {e}")
        return None

def add_subtitles_to_video(video_path, subtitle_path, output_path):
    try:
        command = [
            'ffmpeg', '-i', video_path, '-i', subtitle_path,
            '-c:v', 'copy', '-c:a', 'aac', '-c:s', 'mov_text',
            '-strict', 'experimental', '-y', output_path
        ]
        subprocess.run(command, check=True)
        return True
    except Exception as e:
        print(f"Error adding subtitles to video: {e}")
        return False

if __name__ == '__main__':
    app.run(debug=True)
