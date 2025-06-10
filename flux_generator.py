import requests
import time
import os
from datetime import datetime

class FluxImageGenerator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_version = "v1"
        self.base_url = "https://api.bfl.ml"
        self.model = "flux-pro-1.1"

    def generate_image(self, prompt, width=1024, height=1024):
        # Ensure dimensions are multiples of 32
        width = round(width / 32) * 32
        height = round(height / 32) * 32

        # Validate dimensions
        width = max(256, min(1440, width))
        height = max(256, min(1440, height))

        # Initial request to generate image
        url = f"{self.base_url}/{self.api_version}/{self.model}"
        headers = {
            'accept': 'application/json',
            'x-key': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            'prompt': prompt,
            'width': width,
            'height': height
        }

        try:
            # Make initial request
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            request_id = response.json().get('id')

            if not request_id:
                raise Exception("No request ID received")

                # Poll for results
            image_url = self._poll_for_result(request_id)
            return image_url

        except requests.RequestException as e:
            print(f"Error during API request: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response content: {e.response.text}")
            return None

    def _poll_for_result(self, request_id):
        url = f"{self.base_url}/{self.api_version}/get_result"
        headers = {
            'accept': 'application/json',
            'x-key': self.api_key
        }
        params = {'id': request_id}

        while True:
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                result = response.json()

                if result.get("status") == "Ready":
                    return result.get('result', {}).get('sample')

                print(f"Status: {result.get('status')}")
                time.sleep(0.5)

            except requests.RequestException as e:
                print(f"Error polling for result: {e}")
                return None

def save_image(image_url, output_filename):
    try:
        response = requests.get(image_url)
        response.raise_for_status()

        if os.path.exists(output_filename):
            name, ext = os.path.splitext(output_filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{name}_{timestamp}{ext}"

        with open(output_filename, 'wb') as f:
            f.write(response.content)
        print(f"Image saved as: {output_filename}")
        return output_filename

    except Exception as e:
        print(f"Error saving image: {e}")
        return None

def main():
    # Get API key from environment variable
    api_key = os.getenv('BFL_API_KEY')
    if not api_key:
        print("Please set the BFL_API_KEY environment variable")
        return

        # Create generator instance
    generator = FluxImageGenerator(api_key)

    # Example prompt
    prompt = input("Enter your image prompt: ")

    # Generate image
    print("Generating image...")
    image_url = generator.generate_image(prompt)

    if image_url:
        print(f"Image generated successfully!")
        # Save the image
        save_image(image_url, "generated_image.jpg")
    else:
        print("Failed to generate image")

if __name__ == "__main__":
    main()