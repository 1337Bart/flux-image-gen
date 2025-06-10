from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import uuid
from typing import Optional
import uvicorn
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the FluxImageGenerator class
from flux_generator import FluxImageGenerator

app = FastAPI()

# Create directories
IMAGES_DIR = "generated_images"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/generated_images", StaticFiles(directory="generated_images"), name="generated_images")

# Constants
ALLOWED_MODELS = ["flux-pro-1.1", "flux-pro", "flux-dev"]

# Create templates/index.html
INDEX_HTML = """ 
<!DOCTYPE html> 
<html> 
<head> 
    <title>Image Generator</title> 
    <style> 
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
        } 
        .form-group { 
            margin-bottom: 15px; 
        } 
        label { 
            display: block; 
            margin-bottom: 5px; 
        } 
        input, select { 
            width: 100%; 
            padding: 8px; 
            margin-bottom: 10px; 
        } 
        button { 
            background-color: #4CAF50; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
        } 
        button:disabled { 
            background-color: #cccccc; 
        } 
        #status { 
            margin-top: 20px; 
            padding: 10px; 
            border-radius: 4px; 
        } 
        #result { 
            margin-top: 20px; 
            text-align: center; 
        } 
        #result img { 
            max-width: 100%; 
            height: auto; 
        } 
        .error { 
            color: red; 
            background-color: #ffe6e6; 
            padding: 10px; 
            border-radius: 4px; 
            margin-top: 10px; 
        } 
    </style> 
</head> 
<body> 
    <h1>Image Generator</h1> 
    <div class="form-group"> 
        <label for="prompt">Prompt:</label> 
        <input type="text" id="prompt" required> 
    </div> 
    <div class="form-group"> 
        <label for="width">Width:</label> 
        <input type="number" id="width" value="1024" min="256" max="1440" step="32"> 
    </div> 
    <div class="form-group"> 
        <label for="height">Height:</label> 
        <input type="number" id="height" value="1024" min="256" max="1440" step="32"> 
    </div> 
    <div class="form-group"> 
        <label for="model">Model:</label> 
        <select id="model"> 
            {% for model in models %} 
            <option value="{{ model }}">{{ model }}</option> 
            {% endfor %} 
        </select> 
    </div> 
    <button onclick="generateImage()" id="generateBtn">Generate Image</button> 
    <div id="status"></div> 
    <div id="result"></div> 
 
    <script> 
        async function generateImage() { 
            const prompt = document.getElementById('prompt').value; 
            const width = parseInt(document.getElementById('width').value); 
            const height = parseInt(document.getElementById('height').value); 
            const model = document.getElementById('model').value; 
            const generateBtn = document.getElementById('generateBtn'); 
            const status = document.getElementById('status'); 
            const result = document.getElementById('result'); 
 
            if (!prompt) { 
                status.innerHTML = '<div class="error">Please enter a prompt</div>'; 
                return; 
            } 
 
            generateBtn.disabled = true; 
            status.innerHTML = 'Generating image...'; 
            result.innerHTML = ''; 
 
            try { 
                // Start generation 
                const response = await fetch('/generate', { 
                    method: 'POST', 
                    headers: { 
                        'Content-Type': 'application/json', 
                    }, 
                    body: JSON.stringify({ prompt, width, height, model }), 
                }); 
                const data = await response.json(); 
                 
                // Poll for status 
                const pollInterval = setInterval(async () => { 
                    const statusResponse = await fetch(`/status/${data.generation_id}`); 
                    const statusData = await statusResponse.json(); 
                     
                    status.innerHTML = `Status: ${statusData.status}`; 
                     
                    if (statusData.status === 'completed') { 
                        clearInterval(pollInterval); 
                        result.innerHTML = ` 
                            <img src="/generated_images/${statusData.image_path.split('/').pop()}" alt="Generated Image"> 
                            <br> 
                            <a href="/download/${data.generation_id}" download>Download Image</a> 
                        `; 
                        generateBtn.disabled = false; 
                    } else if (statusData.status === 'failed') { 
                        clearInterval(pollInterval); 
                        status.innerHTML = `<div class="error">Generation failed: ${statusData.error || 'Unknown error'}</div>`; 
                        generateBtn.disabled = false; 
                    } 
                }, 1000); 
            } catch (error) { 
                status.innerHTML = `<div class="error">Error: ${error.message}</div>`; 
                generateBtn.disabled = false; 
            } 
        } 
    </script> 
</body> 
</html> 
"""

# Write the template file
with open("templates/index.html", "w") as f:
    f.write(INDEX_HTML)

# Your existing code for ImageRequest, ImageResponse, and active_generations here...

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "models": ALLOWED_MODELS}
    )

# Modify your generate_image endpoint to accept the model parameter
class ImageRequest(BaseModel):
    prompt: str
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    model: Optional[str] = "flux-pro-1.1"

# Update your generate_image_task function to use the selected model
async def generate_image_task(generation_id: str, prompt: str, width: int, height: int, model: str):
    try:
        logger.info(f"Starting image generation for ID: {generation_id}")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Dimensions: {width}x{height}")
        logger.info(f"Model: {model}")

        # Update generator model
        generator.model = model

        # Rest of your existing generate_image_task code...

# Update your generate endpoint
@app.post("/generate", response_model=ImageResponse)
async def generate_image(request: ImageRequest, background_tasks: BackgroundTasks):
    logger.info("Received new image generation request")

    if request.model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail="Invalid model selected")

    generation_id = str(uuid.uuid4())

    active_generations[generation_id] = {
        "status