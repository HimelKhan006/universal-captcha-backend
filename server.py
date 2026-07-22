import os
import random
import urllib.request
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydub import AudioSegment
from pydub.effects import normalize
import speech_recognition as sr

app = Flask(__name__)
CORS(app)  # Allows browser extension cross-origin calls

# --- CONFIGURATION OPTIONS ---
SOLVE_MODE = "words"  # Options: "words", "numbers", "all"
HUMAN_ERROR_RATE = 0.15  # 15% chance to submit an intentional mistake to reset trackers
# ----------------------------

# Set directory paths dynamically depending on host platform (Linux vs. Windows)
if os.name != 'nt':
    MP3_FILE = "/tmp/api_voice.mp3"
    WAV_FILE = "/tmp/api_voice.wav"
else:
    MP3_FILE = os.path.join(os.getcwd(), "api_voice.mp3")
    WAV_FILE = os.path.join(os.getcwd(), "api_voice.wav")

def detect_challenge_type(text):
    """Classifies if the transcribed text represents a digit sequence or standard words."""
    if not text:
        return "unknown"
    
    cleaned_text = text.lower().replace("-", " ").replace(",", " ").replace(".", " ")
    words = cleaned_text.split()
    
    number_keywords = {
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "oh", "to", "too", "for", "fore", "ate", "won"
    }
    
    number_word_count = sum(1 for word in words if word.isdigit() or word in number_keywords)
    
    if len(words) > 0 and (number_word_count / len(words)) >= 0.4:
        return "numbers"
    return "words"

def introduce_human_error(text):
    """Intentionally corrupts the response slightly to mimic a human typing mistake."""
    if not text:
        return text
    if text.isdigit():
        last_digit = int(text[-1])
        new_digit = str((last_digit + 1) % 10)
        return text[:-1] + new_digit
    else:
        return text + "x"

def normalize_transcription(text):
    """Parses audio transcription directly to digits/normalized texts."""
    if not text:
        return ""
    
    cleaned_text = text.lower().replace("-", " ").replace(",", " ").replace(".", " ")
    words = cleaned_text.split()
    
    word_to_digit = {
        "zero": "0", "oh": "0", "no": "0", "go": "0", "hero": "0",
        "one": "1", "won": "1", "on": "1", "when": "1", "want": "1",
        "two": "2", "to": "2", "too": "2", "do": "2", "through": "2",
        "three": "3", "tree": "3", "the": "3", "key": "3",
        "four": "4", "for": "4", "fore": "4", "or": "4", "more": "4",
        "file": "5", "fire": "5", "fine": "5", "find": "5",
        "sex": "6", "clicks": "6", "fix": "6", "mix": "6",
        "send": "7", "save": "7", "safe": "7",
        "ate": "8", "h": "8", "height": "8", "it": "8", "hate": "8",
        "night": "9", "line": "9", "mind": "9", "nice": "9", "double-u": "w"
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
        urllib.request.urlretrieve(audio_url, MP3_FILE)
        
        sound = AudioSegment.from_mp3(MP3_FILE)
        
        try:
            # Cut standard low/high frequency rumbles to isolate clean voice signals (150Hz - 3000Hz)
            sound = sound.high_pass_filter(150).low_pass_filter(3000)
        except Exception:
            pass
            
        try:
            sound = normalize(sound)
        except Exception:
            pass
            
        sound.export(WAV_FILE, format="wav")
        
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        
        with sr.AudioFile(WAV_FILE) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
            raw_text = recognizer.recognize_google(audio_data, language="en-US")
            
        challenge_type = detect_challenge_type(raw_text)
        print(f"[*] Detected challenge type: {challenge_type.upper()}")
        
        if SOLVE_MODE != "all" and challenge_type != SOLVE_MODE:
            print(f"[!] Mismatch: Configured to solve {SOLVE_MODE.upper()} only. Requesting reload.")
            return jsonify({"error": f"Skipped {challenge_type} challenge based on SOLVE_MODE"}), 400
            
        transcription = normalize_transcription(raw_text)
        
        if random.random() < HUMAN_ERROR_RATE:
            print("[!] Simulating human error: Intentionally corrupting response...")
            transcription = introduce_human_error(transcription)

        print(f"[+] Successfully prepared challenge output: {transcription}")
        return jsonify({"solution": transcription})
        
    except Exception as e:
        print(f"[-] Solving error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(MP3_FILE):
            try: os.remove(MP3_FILE)
            except OSError: pass
        if os.path.exists(WAV_FILE):
            try: os.remove(WAV_FILE)
            except OSError: pass

if __name__ == "__main__":
    # Binds to Port 10000 locally or matches dynamic cloud system allocation
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)