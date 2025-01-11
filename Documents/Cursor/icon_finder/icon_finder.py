import pyautogui
import cv2
import numpy as np
import time
import base64
from anthropic import Anthropic
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Directory structure constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
DEBUG_DIR = os.path.join(SCREENSHOTS_DIR, "debug")
GRID_DIR = os.path.join(SCREENSHOTS_DIR, "grid")
PROMPTS_DIR = os.path.join(BASE_DIR, "..", "prompts")
RESPONSES_DIR = os.path.join(BASE_DIR, "responses")

# Ensure directories exist
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(GRID_DIR, exist_ok=True)
os.makedirs(RESPONSES_DIR, exist_ok=True)

# Initialize Anthropic client
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class GridVisualizer:
    def __init__(self, grid_spacing=100):
        self.grid_spacing = grid_spacing
        
    def create_grid_overlay(self, screenshot):
        """Create a grid overlay on the screenshot with coordinate labels."""
        grid_image = screenshot.copy()
        draw = ImageDraw.Draw(grid_image)
        width, height = screenshot.size
        
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

        # Draw vertical lines and x-coordinates
        for x in range(0, width, self.grid_spacing):
            draw.line([(x, 0), (x, height)], fill='red', width=2)
            draw.rectangle([(x + 5, 5), (x + 60, 25)], fill='white')
            draw.text((x + 5, 5), str(x), fill='red', font=font)

        # Draw horizontal lines and y-coordinates
        for y in range(0, height, self.grid_spacing):
            draw.line([(0, y), (width, y)], fill='red', width=2)
            draw.rectangle([(5, y + 5), (60, y + 25)], fill='white')
            draw.text((5, y + 5), str(y), fill='red', font=font)

        return grid_image

    def draw_crosshair(self, image, x, y, size=20, color='blue'):
        """Draw a crosshair at the specified coordinates."""
        draw = ImageDraw.Draw(image)
        draw.line([(x - size, y), (x + size, y)], fill=color, width=3)
        draw.line([(x, y - size), (x, y + size)], fill=color, width=3)
        text = f"({x}, {y})"
        draw.rectangle([(x + 5, y + 5), (x + 150, y + 25)], fill='white')
        draw.text((x + 5, y + 5), text, fill=color, font=ImageFont.truetype("arial.ttf", 16))
        return image

class ClaudeInterface:
    def __init__(self, anthropic_client):
        self.client = anthropic_client
        self.training_file = os.path.join(BASE_DIR, "training_examples.json")
        with open(os.path.join(PROMPTS_DIR, 'system_prompt.md'), 'r') as f:
            self.system_prompt = f.read()
        
    def load_training_examples(self):
        """Load training examples from JSON file."""
        if os.path.exists(self.training_file):
            with open(self.training_file, 'r') as f:
                return json.loads(f.read())
        return {"examples": []}
    
    def save_training_example(self, screenshot_path, target_app, correct_coords, explanation):
        """Save a new training example."""
        examples = self.load_training_examples()
        examples["examples"].append({
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "target_app": target_app,
            "screenshot_path": screenshot_path,
            "correct_coords": correct_coords,
            "explanation": explanation
        })
        with open(self.training_file, 'w') as f:
            json.dump(examples, f, indent=4)

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_screenshot(self, screenshot_path, target_app, training_mode=False):
        base64_image = self.encode_image(screenshot_path)
        
        # Load and combine prompts
        with open(os.path.join(PROMPTS_DIR, 'coordinate_guide.md'), 'r') as f:
            coordinate_guide = f.read()
        
        with open(os.path.join(PROMPTS_DIR, 'task_prompt.md'), 'r') as f:
            task_prompt = f.read().format(target_app=target_app)
        
        # Add training examples if available
        training_examples = ""
        if training_mode:
            examples = self.load_training_examples()
            if examples["examples"]:
                training_examples = "\n\n## Training Examples\n"
                for ex in examples["examples"]:
                    training_examples += f"""
Example for {ex['target_app']}:
- Correct coordinates: {ex['correct_coords']}
- How to measure: {ex['explanation']}
"""
        
        message = f"{task_prompt}\n\n{coordinate_guide}{training_examples}"

        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,
            system=self.system_prompt,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64_image
                    }}
                ]
            }]
        )
        
        return response.content[0].text

class CoordinateClicker:
    @staticmethod
    def validate_and_click(x, y):
        screen_width, screen_height = pyautogui.size()
        print(f"Debug - Screen dimensions: {screen_width}x{screen_height}")
        print(f"Debug - Target coordinates: ({x}, {y})")
        
        if 0 <= x <= screen_width and 0 <= y <= screen_height:
            confirm = input("\nWould you like to proceed with the click? (y/n): ")
            if confirm.lower() == 'y':
                pyautogui.moveTo(x, y, duration=0.5)
                pyautogui.click()
                return True
        return False

def main():
    print("Please ensure the target application is visible on your screen.")
    time.sleep(2)
    
    training_mode = input("Would you like to run in training mode? (y/n): ").lower() == 'y'
    target_app = input("Enter the name of the application to click (e.g., 'Google Chrome'): ")
    
    # Initialize components
    grid_visualizer = GridVisualizer()
    claude_interface = ClaudeInterface(anthropic)
    
    # Take and process screenshot
    screenshot = pyautogui.screenshot()
    grid_screenshot = grid_visualizer.create_grid_overlay(screenshot)
    
    # Create timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Define all paths
    response_file = os.path.join(BASE_DIR, "responses", f"response_{timestamp}.txt")
    original_path = os.path.join(DEBUG_DIR, "original.png")
    grid_path = os.path.join(GRID_DIR, "current.png")
    verification_path = os.path.join(DEBUG_DIR, "sent_to_claude.png")
    target_path = os.path.join(DEBUG_DIR, "with_target.png")
    
    # Save screenshots
    screenshot.save(original_path)
    grid_screenshot.save(grid_path)
    grid_screenshot.save(verification_path)
    
    print(f"Processing screenshot with AI analysis...")
    response = claude_interface.analyze_screenshot(grid_path, target_app, training_mode=training_mode)
    
    # Save Claude's response with metadata
    with open(response_file, 'w', encoding='utf-8') as f:
        f.write(f"Target Application: {target_app}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Original Screenshot: {original_path}\n")
        f.write(f"Grid Screenshot: {grid_path}\n")
        f.write("="*50 + "\n\n")
        f.write(response)
    
    print("\nAI Response:")
    print(response)
    print(f"\nFull response saved to: {response_file}")
    
    # Parse response for coordinates
    if "COORDINATES:" in response:
        coords_line = [line for line in response.split('\n') if "COORDINATES:" in line][0]
        coords = coords_line.split("COORDINATES:")[1].strip().strip('"')
        
        if coords.lower() != "not found" and ',' in coords:
            try:
                x, y = map(int, coords.split(','))
                grid_with_target = grid_visualizer.draw_crosshair(grid_screenshot, x, y)
                grid_with_target.save(target_path)
                print(f"Saved visualization to {target_path}")
                
                if training_mode:
                    is_correct = input("\nAre these coordinates correct? (y/n): ").lower() == 'y'
                    if not is_correct:
                        print("\nPlease provide the correct coordinates and explanation:")
                        correct_x = int(input("Correct X coordinate: "))
                        correct_y = int(input("Correct Y coordinate: "))
                        explanation = input("Explain how to measure these coordinates correctly: ")
                        
                        # Save the training example
                        claude_interface.save_training_example(
                            grid_path,
                            target_app,
                            f"{correct_x},{correct_y}",
                            explanation
                        )
                        print("\nTraining example saved!")
                        
                        # Draw the correct coordinates
                        grid_with_correct = grid_visualizer.draw_crosshair(grid_screenshot, correct_x, correct_y, color='green')
                        grid_with_correct.save(os.path.join(DEBUG_DIR, "correct_target.png"))
                        return
                
                CoordinateClicker.validate_and_click(x, y)
            except ValueError:
                print("Could not parse coordinates from AI response")
    else:
        print("No coordinates found in AI response")

if __name__ == "__main__":
    main()