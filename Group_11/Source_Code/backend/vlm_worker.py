import threading
import time
from typing import Optional, Tuple
from chromadb_utils import ingest_vlm_json

# Assuming you have:
# - vlm_buffer: instance of VLMFrameBuffer
# - call_gemini_api(frame_bytes) -> returns result (text/embedding)
# - store_in_vector_db(result) -> stores result in your DB/file

class VLMWorker:
    def __init__(self, vlm_buffer, min_interval: float = 21.0):
        """
        vlm_buffer: VLMFrameBuffer instance
        min_interval: minimum seconds between API calls (rate limit)
        """
        self.buffer = vlm_buffer
        self.min_interval = min_interval
        self.last_call_time = 0.0
        self._stop_event = threading.Event()

    def stop(self):
        """Stop the worker cleanly."""
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            item: Optional[Tuple[float, bytes]] = self.buffer.pop()
            
            if item is None:
                # buffer empty → sleep briefly to avoid busy loop
                time.sleep(0.1)
                continue

            timestamp, frame_bytes = item
            now = time.time()

            # enforce minimum interval between API calls
            if now - self.last_call_time < self.min_interval:
                # put frame back at the front and wait
                with self.buffer.lock:
                    self.buffer.buffer.appendleft((timestamp, frame_bytes))
                time.sleep(self.min_interval - (now - self.last_call_time))
                continue

            # Call Gemini API (blocking)
            try:
                result = call_gemini_api(frame_bytes)
            except Exception as e:
                print(f"[VLMWorker] Error calling Gemini API: {e}")
                continue

            # Store result in vector DB
            try:
                ingest_vlm_json(vlm_responses=[result])
            except Exception as e:
                print(f"[VLMWorker] Error storing result: {e}")

            # Update last call time
            self.last_call_time = time.time()



import os, io
from google import genai
from PIL import Image
def call_gemini_api(frame_bytes):

    #Convert bytes to PIL image for gemini
    image = Image.open(io.BytesIO(frame_bytes))

    # api_key = "AIzaSyB9a-9p1RTbLyJ06ZjIB6cEMXykn4S_Y0Y"
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    PROMPT = """
    You are analyzing a CCTV frame.

    Return ONLY a JSON object.

    Schema:

    {
    "people_count": int,
    "people_description": [],
    "vehicle_count": int,
    "vehicle_type": null|string,
    "vehicle_color": null|string,
    "clothing": [],
    "carrying_items": [],
    "activity": null|string,
    "interaction": null|string,
    "location": null|string,
    "time_of_day": null|string,
    "anomaly": null|string,
    "summary": string
    }

    Rules:
    - Use English only
    - If unknown return null
    - Do not output anything except JSON
    """

    # Open the image using Pillow
    # try:
    #     img = Image.open(image_path)
    # except FileNotFoundError:
    #     print(f"Error: The file '{image_path}' was not found.")
    #     exit()

    # This model can process both text and images
    model_name = "gemini-2.5-flash"

    from pydantic import BaseModel
    from typing import List, Optional
    import json

    class ImageCaption(BaseModel):
        people_count: int
        people_description: List[str]
        vehicle_count: int
        vehicle_type: Optional[str]
        vehicle_color: Optional[str]
        clothing: List[str]
        carrying_items: List[str]
        activity: Optional[str]
        interaction: Optional[str]
        location: Optional[str]
        time_of_day: Optional[str]
        anomaly: Optional[str]
        summary: str

    response = client.models.generate_content(
        model=model_name,
        contents=[PROMPT, image],
        config={
            'response_mime_type': 'application/json',
            'response_schema': ImageCaption,
        }
    )

    # Convert to dict, then to a pretty-printed string
    analysis_dict = response.parsed.model_dump()
    json_response = json.dumps(analysis_dict, indent=2)

    print(f"\n\n{json_response}\n\n")

    with open("gemini_response.txt", "a", encoding="utf-8") as f:
        f.write(json_response + "\n\n")

    return json_response