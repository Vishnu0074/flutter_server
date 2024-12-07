from flask import Flask, request, jsonify
import time
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable, VideoUnavailable
import google.generativeai as genai
import re

# Configure Generative AI API
genai.configure(api_key="AIzaSyCONr9BzIBsUnVaAGJ1_1zcu2erGu-ji-c")  # Replace with your API Key

app = Flask(__name__)

# Chatbot Class
class GenerativeAIChatbot:
    def __init__(self, model_name="gemini-1.5-flash"):
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            },
        )
        self.chat_session = self.model.start_chat(history=[])

    def send_message(self, message):
        """Send a message to the chatbot and get the response."""
        response = self.chat_session.send_message(message)
        return response.text

# Function to extract video ID from a YouTube link
def extract_video_id(youtube_url):
    match = re.search(r"v=([a-zA-Z0-9_-]+)", youtube_url)
    return match.group(1) if match else None

# Function to fetch YouTube transcript
def get_youtube_transcript(video_id):
    retries = 3
    for attempt in range(retries):
        try:
            # Fetch the list of available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Get the autogenerated transcript in Hindi or English
            try:
                transcript = transcript_list.find_generated_transcript(['hi', 'en', 'ml']).fetch()
                return " ".join([entry['text'] for entry in transcript])
            except NoTranscriptAvailable:
                return "No autogenerated transcript available for the specified languages."

        except TranscriptsDisabled:
            return "Captions are disabled for this video."
        except VideoUnavailable:
            return "The video is unavailable."
        except Exception as e:
            time.sleep(2)  # Wait before retrying
            if attempt == retries - 1:
                return f"Failed to fetch transcript after multiple attempts. Error: {str(e)}"

# API Endpoint
@app.route("/", methods=["POST"])
def summarize_video():
    data = request.json
    youtube_url = data.get("youtube_url")

    if not youtube_url:
        return jsonify({"error": "YouTube URL is required"}), 400

    # Extract video ID
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    # Fetch transcript
    transcript = get_youtube_transcript(video_id)
    if transcript.startswith("Error") or transcript.startswith("No"):
        return jsonify({"error": transcript}), 400

    # Process transcript with Generative AI
    chatbot_input = f"summarize: {transcript}"
    chatbot = GenerativeAIChatbot()
    try:
        response = chatbot.send_message(chatbot_input)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": f"Chatbot interaction failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)