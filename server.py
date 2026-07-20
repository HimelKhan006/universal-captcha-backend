import os
import urllib.request
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydub import AudioSegment
import speech_recognition as sr

app = Flask(__name__)
CORS(app)  # Allows the extension to call this server safely

# We use the Linux /tmp directory for temporary audio processing in the cloud
MP3_FILE = "/tmp/api_voice.mp3"
WAV_FILE = "/tmp/api_voice.wav"

def normalize_transcription(text):
    """
    Parses Google Web Speech API outputs and maps English number words, 
    homophones, and common acoustic mishearings directly to numeric strings.
    """
    if not text:
        return ""
    
    cleaned_text = text.lower().replace("-", " ").replace(",", " ").replace(".", " ")
    words = cleaned_text.split()
    
    word_to_digit = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "oh": "0", "no": "0", "go": "0", "hero": "0",
        "won": "1", "on": "1", "when": "1", "want": "1",
        "to": "2", "too": "2", "do": "2", "through": "2",
        "free": "3", "tree": "3", "the": "3", "key": "3",
        "for": "4", "fore": "4", "or": "4", "more": "4",
        "file": "5", "fire": "5", "fine": "5", "find": "5",
        "sex": "6", "clicks": "6", "fix": "6", "mix": "6",
        "send": "7", "save": "7", "safe": "7",
        "ate": "8", "h": "8", "height": "8", "it": "8", "hate": "8",
        "night": "9", "line": "9", "mind": "9", "nice": "9", "find": "9"
    }
    
    digit_only_result = []
    for word in words:
        if word.isdigit():
            digit_only_result.append(word)
        elif word in word_to_digit:
            digit_only_result.append(word_to_digit[word])
            
    if digit_only_result:
        return "".join(digit_only_result)
        
    return text.strip()

@app.route("/solve", methods=["GET"])
def solve():
    audio_url = request.args.get("url")
    if not audio_url:
        return jsonify({"error": "No URL provided"}), 400
        
    try:
        # Download the audio challenge
        urllib.request.urlretrieve(audio_url, MP3_FILE)
        
        # Convert MP3 to WAV
        sound = AudioSegment.from_mp3(MP3_FILE)
        sound.export(WAV_FILE, format="wav")
        
        # Process speech-to-text
        recognizer = sr.Recognizer()
        with sr.AudioFile(WAV_FILE) as source:
            audio_data = recognizer.record(source)
            raw_text = recognizer.recognize_google(audio_data)
            
        transcription = normalize_transcription(raw_text)
        print(f"[+] Successfully solved challenge: {transcription}")
        return jsonify({"solution": transcription})
        
    except Exception as e:
        print(f"[-] Solving error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        # File Cleanup
        if os.path.exists(MP3_FILE):
            os.remove(MP3_FILE)
        if os.path.exists(WAV_FILE):
            os.remove(WAV_FILE)

if __name__ == "__main__":
    # Render binds dynamically to the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)