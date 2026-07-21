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
            "zero": "0", "oh": "0",
        "one": "1", "won": "1",
        "two": "2", "to": "2", "too": "2",
        "three": "3",
        "four": "4", "for": "4", "fore": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8", "ate": "8",
        "nine": "9",
        "double-u": "w"
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
        # 1. Switch context to the active reCAPTCHA anchor
        driver.switch_to.frame(anchor_iframe)
        
        checkbox = wait.until(EC.element_to_be_clickable((By.ID, "recaptcha-anchor")))
        print("[*] Clicking 'I'm not a robot' checkbox...")
        checkbox.click()
        time.sleep(1.2)
        
        if checkbox.get_attribute("aria-checked") == "true":
            print("[+] Verified instantly without a prompt.")
            return True

        # 2. Switch back to the main document context
        driver.switch_to.default_content()
        
        # 3. Locate and switch into the challenge popup iframe
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe[src*='/recaptcha/'][src*='/bframe']")))
        
        # 4. Click the Audio (headphones) icon (only if not already inside the audio panel)
        try:
            audio_btn = wait.until(EC.element_to_be_clickable((By.ID, "recaptcha-audio-button")))
            print("[*] Accessing the audio option...")
            audio_btn.click()
            time.sleep(1.2)
        except Exception:
            pass
            
        # 5. Begin solving loop to handle multi-step verifications
        for attempt in range(1, max_solve_attempts + 1):
            print(f"[*] Solving attempt {attempt} of {max_solve_attempts}...")
            
            try:
                # Access the audio download link
                download_elem = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rc-audiochallenge-tdownload-link")))
                audio_url = download_elem.get_attribute("href")
                
                if not audio_url:
                    print("[-] Unable to locate speech source link.")
                    return False
                    
                print("[*] Fetching audio challenge...")
                urllib.request.urlretrieve(audio_url, MP3_FILE)
                
                # Run transcription process
                raw_transcription = convert_and_transcribe()
                if not raw_transcription:
                    print("[-] Local transcription failed. Requesting a reload challenge...")
                    try:
                        reload_btn = driver.find_element(By.ID, "recaptcha-reload-button")
                        reload_btn.click()
                        time.sleep(1.5)
                    except Exception:
                        pass
                    continue
                
                # Clean and translate the text transcript into numbers
                transcription = normalize_transcription(raw_transcription)
                print(f"[+] Decoded text: '{transcription}'")
                
                # Locate response field, clear previous inputs, and type the transcription
                response_box = wait.until(EC.presence_of_element_located((By.ID, "audio-response")))
                response_box.clear()
                response_box.send_keys(transcription)
                
                # Submit solution
                verify_btn = wait.until(EC.element_to_be_clickable((By.ID, "recaptcha-verify-button")))
                print("[*] Submitting solution...")
                verify_btn.click()
                time.sleep(2.0)
                
                # Switch to main context, then anchor iframe to verify state
                driver.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe[src*='/recaptcha/'][src*='/anchor']")))
                checkbox = wait.until(EC.presence_of_element_located((By.ID, "recaptcha-anchor")))
                
                if checkbox.get_attribute("aria-checked") == "true":
                    print("[+] reCAPTCHA verified successfully.")
                    return True
                else:
                    print("[-] Multi-challenge or secondary verification requested. Continuing loop...")
                    # Return back to bframe for the next attempt
                    driver.switch_to.default_content()
                    wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe[src*='/recaptcha/'][src*='/bframe']")))
                    
            except Exception as e:
                print(f"[-] Challenge loop error on attempt {attempt}: {e}")
                try:
                    driver.switch_to.default_content()
                    wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe[src*='/recaptcha/'][src*='/bframe']")))
                except Exception:
                    break
        
        print("[-] Exceeded maximum verification retries.")
        return False

    except Exception as e:
        print(f"[-] Error solving CAPTCHA instance: {e}")
        return False
    finally:
        driver.switch_to.default_content()

def monitor_page_for_captcha(driver):
    """Runs a polling loop, scanning the active page for unsolved CAPTCHA instances."""
    print(f"[*] AI Monitor started. Listening for reCAPTCHAs on the active page...")
    
    while True:
        try:
            # Check for standard or enterprise anchor iframes
            anchor_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='/recaptcha/'][src*='/anchor']")
            
            if anchor_iframes:
                active_iframe = anchor_iframes[0]
                
                # Check current state of the checkbox within the iframe
                driver.switch_to.frame(active_iframe)
                checkbox = driver.find_element(By.ID, "recaptcha-anchor")
                is_checked = checkbox.get_attribute("aria-checked") == "true"
                driver.switch_to.default_content() # Always switch back to standard context
                
                if not is_checked:
                    print("[+] Unsolved reCAPTCHA found on page. Starting solver...")
                    solve_recaptcha_instance(driver, active_iframe)
            
        except Exception as e:
            pass
            
        time.sleep(POLL_INTERVAL)

def main():
    driver = setup_stealth_browser()
    driver.get(TARGET_URL)
    
    try:
        monitor_page_for_captcha(driver)
    except KeyboardInterrupt:
        print("\n[*] Background daemon terminated manually.")
    finally:
        pass

if __name__ == "__main__":
    main()
    # Render binds dynamically to the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
