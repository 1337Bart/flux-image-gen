from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import uuid
from typing import Optional
import logging
from datetime import datetime
import uvicorn

from frontend import get_index_page, ALLOWED_MODELS
from flux_generator import FluxImageGenerator
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the FluxImageGenerator class from our previous code
from flux_generator import FluxImageGenerator

app = FastAPI()

# Create a directory for storing generated images
IMAGES_DIR = "generated_images"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static directories
app.mount("/generated_images", StaticFiles(directory=IMAGES_DIR), name="generated_images")

# Store ongoing generations
active_generations = {}

class ImageRequest(BaseModel):
    prompt: str
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    model: Optional[str] = "flux-pro-1.1"

class ImageResponse(BaseModel):
    generation_id: str
    status: str
    image_path: Optional[str] = None
    error: Optional[str] = None  # Added error field

# Initialize the generator
api_key = os.getenv('BFL_API_KEY')
if not api_key:
    raise Exception("Please set the BFL_API_KEY environment variable")
generator = FluxImageGenerator(api_key)
app.get("/")(get_index_page)

async def generate_image_task(generation_id: str, prompt: str, width: int, height: int, model: str):
    try:
        logger.info(f"Starting image generation for ID: {generation_id}")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Dimensions: {width}x{height}")
        logger.info(f"Model: {model}")

        # Update generator model
        generator.model = model

        # Generate the image
        image_url = generator.generate_image(prompt, width, height)

        if image_url:
            logger.info(f"Image URL received: {image_url}")

            # Create a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{generation_id}_{timestamp}.jpg"
            filepath = os.path.join(IMAGES_DIR, filename)

            logger.info(f"Saving image to: {filepath}")

            # Save the image
            saved_path = generator.save_image(image_url, filepath)

            if saved_path:
                logger.info(f"Image saved successfully at: {saved_path}")
                active_generations[generation_id] = {
                    "status": "completed",
                    "image_path": saved_path
                }
            else:
                error_msg = "Failed to save image"
                logger.error(error_msg)
                active_generations[generation_id] = {
                    "status": "failed",
                    "error": error_msg
                }
        else:
            error_msg = "Failed to generate image - no URL received"
            logger.error(error_msg)
            active_generations[generation_id] = {
                "status": "failed",
                "error": error_msg
            }
    except Exception as e:
        error_msg = f"Error during image generation: {str(e)}"
        logger.error(error_msg)
        active_generations[generation_id] = {
            "status": "failed",
            "error": error_msg
        }

@app.post("/generate", response_model=ImageResponse)
async def generate_image(request: ImageRequest, background_tasks: BackgroundTasks):
    if request.model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail="Invalid model selected")

    generation_id = str(uuid.uuid4())
    active_generations[generation_id] = {"status": "processing"}

    background_tasks.add_task(
        generate_image_task,
        generation_id,
        request.prompt,
        request.width,
        request.height,
        request.model
    )

    return ImageResponse(generation_id=generation_id, status="processing")

@app.get("/status/{generation_id}", response_model=ImageResponse)
async def get_status(generation_id: str):
    if generation_id not in active_generations:
        raise HTTPException(status_code=404, detail="Generation ID not found")

    generation = active_generations[generation_id]

    return ImageResponse(
        generation_id=generation_id,
        status=generation["status"],
        image_path=generation.get("image_path"),
        error=generation.get("error")
    )

@app.get("/download/{generation_id}")
async def download_image(generation_id: str):
    if generation_id not in active_generations:
        raise HTTPException(status_code=404, detail="Generation ID not found")

    generation = active_generations[generation_id]

    if generation["status"] == "failed":
        raise HTTPException(
            status_code=400,
            detail=generation.get("error", "Image generation failed")
        )

    if generation["status"] != "completed":
        raise HTTPException(status_code=400, detail="Image generation not completed")

    if not generation.get("image_path"):
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(generation["image_path"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 