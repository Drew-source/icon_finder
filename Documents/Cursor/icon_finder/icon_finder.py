import os
import sys
import time
from datetime import datetime
import pyautogui
from PIL import Image, ImageDraw, ImageFont
import base64
from anthropic import Anthropic
import dotenv
import logging

# Load environment variables from project root
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
dotenv.load_dotenv(dotenv_path)

# Verify API key is available
if not os.getenv('ANTHROPIC_API_KEY'):
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables. Please ensure .env file exists with the key.")

# Directory structure constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")  # Move data dir to project root
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "screenshots")
RESPONSES_DIR = os.path.join(DATA_DIR, "responses")
PROMPTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "prompts")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(RESPONSES_DIR, exist_ok=True)

def get_timestamp():
    """Get formatted timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

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

    def draw_crosshair(self, image, x, y, size=40, color='lime'):
        """Draw a crosshair at the specified coordinates."""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # Draw thicker crosshair lines
        draw.line([(x - size, y), (x + size, y)], fill=color, width=4)
        draw.line([(x, y - size), (x, y + size)], fill=color, width=4)
        
        # Draw circle around center
        circle_size = 15
        draw.ellipse([(x - circle_size, y - circle_size), 
                     (x + circle_size, y + circle_size)], 
                     outline=color, width=3)
        
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Draw text with white background
        text = f"({x}, {y})"
        
        # Estimate text dimensions (more reliable than textbbox)
        text_width = len(text) * 15  # Approximate width based on character count
        text_height = 30  # Fixed height for our font size
        
        # Default position is to the right and down
        text_x = x + 15
        text_y = y + 15
        
        # Adjust position if too close to edges
        if text_x + text_width + 10 > width:
            text_x = x - text_width - 15
        if text_y + text_height + 10 > height:
            text_y = y - text_height - 15
            
        # Draw white background rectangle
        padding = 5
        draw.rectangle([
            (text_x - padding, text_y - padding),
            (text_x + text_width + padding, text_y + text_height + padding)
        ], fill='white')
        
        # Draw text
        draw.text((text_x, text_y), text, fill=color, font=font)
        
        return image

class ClaudeInterface:
    def __init__(self):
        self.logger = logging.getLogger('IconFinder')
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self.client = Anthropic(api_key=api_key)
        self.logger.info("Claude client initialized successfully")
        self.load_prompts()
        
    def load_prompts(self):
        """Load system and task prompts from files"""
        try:
            with open(os.path.join(PROMPTS_DIR, "system_prompt.md"), "r") as f:
                self.system_prompt = f.read()
                
            with open(os.path.join(PROMPTS_DIR, "task_prompt.md"), "r") as f:
                self.task_prompt_template = f.read()
                
            with open(os.path.join(PROMPTS_DIR, "coordinate_guide.md"), "r") as f:
                self.coordinate_guide = f.read()
            
            # Try to load meta learning context if it exists
            meta_learning_path = os.path.join(PROMPTS_DIR, "meta_learning_context.md")
            self.meta_learning_context = ""
            self.logger.debug(f"Looking for meta-learning context at: {meta_learning_path}")
            if os.path.exists(meta_learning_path):
                self.logger.debug("Meta-learning context file found")
                with open(meta_learning_path, "r") as f:
                    self.meta_learning_context = f.read()
                self.logger.debug(f"Loaded meta-learning context ({len(self.meta_learning_context)} chars)")
            else:
                self.logger.warning("Meta-learning context file not found")
            
            self.logger.info("Prompts loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load prompts: {str(e)}")
            raise

    def analyze_screenshot(self, screenshot_path, target_app):
        """Analyze a screenshot using Claude"""
        try:
            # Clear previous responses and screenshots
            timestamp = get_timestamp()
            attempt_dir = os.path.join(SCREENSHOTS_DIR, timestamp)
            os.makedirs(attempt_dir, exist_ok=True)
            
            # Clear log file before new attempt
            log_file = os.path.join(os.path.dirname(BASE_DIR), "logs", "icon_finder.log")
            if os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    f.write(f"=== New attempt started at {timestamp} ===\n")
            
            self.logger.info(f"Starting Claude analysis for target: {target_app}")
            timestamp = get_timestamp()
            
            # Format task prompt
            task_prompt = self.task_prompt_template.format(
                task_target=target_app
            )
            
            # Combine all prompts in a meaningful order
            message = task_prompt + "\n\n" + self.coordinate_guide
            if self.meta_learning_context:
                self.logger.debug("Adding meta-learning context to message")
                message = self.meta_learning_context + "\n\n" + message
            else:
                self.logger.warning("No meta-learning context available to add to message")
            
            # Save the prompt for debugging
            prompt_path = os.path.join(RESPONSES_DIR, f"prompt_{timestamp}.txt")
            with open(prompt_path, "w") as f:
                f.write(message)
            self.logger.debug(f"Saved prompt to: {prompt_path}")
            
            # Read the image file
            with open(screenshot_path, "rb") as f:
                image_data = f.read()
            
            # Get Claude's analysis
            self.logger.info("Sending request to Claude...")
            response = self.client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=4096,
                temperature=0,
                system=self.system_prompt,
                messages=[{
                    "role": "user", 
                    "content": [
                        {
                            "type": "text",
                            "text": message
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64.b64encode(image_data).decode()
                            }
                        }
                    ]
                }]
            )
            
            # Save and process the response
            response_text = response.content[0].text if response.content else "No response received"
            self.logger.debug(f"Received response from Claude: {response_text[:100]}...")
            
            # Save full response details
            response_path = os.path.join(RESPONSES_DIR, f"response_{timestamp}.txt")
            with open(response_path, "w", encoding='utf-8') as f:
                f.write(f"TARGET: {target_app}\n")
                f.write(f"TIMESTAMP: {timestamp}\n")
                f.write(f"SCREENSHOT: {screenshot_path}\n")
                f.write("\nRESPONSE:\n")
                f.write(response_text)
            self.logger.debug(f"Saved response to: {response_path}")
            
            # Validate response format
            if not response_text or "COORDINATES:" not in response_text:
                self.logger.warning("Response missing COORDINATES field")
                error_response = "COORDINATES: not found\nEXPLANATION: Could not locate the target in the image."
                return error_response, timestamp
                
            return response_text, timestamp
            
        except Exception as e:
            self.logger.error(f"Error in analyze_screenshot: {str(e)}")
            error_response = "COORDINATES: not found\nEXPLANATION: An error occurred during analysis."
            return error_response, timestamp

    def save_response(self, response_text, timestamp):
        """Save response text to file with UTF-8 encoding"""
        response_path = os.path.join(RESPONSES_DIR, f"response_{timestamp}.txt")
        with open(response_path, 'w', encoding='utf-8') as f:
            f.write(response_text)
        return response_path

    def save_prompt(self, prompt_text, timestamp):
        """Save prompt text to file with UTF-8 encoding"""
        prompt_path = os.path.join(RESPONSES_DIR, f"prompt_{timestamp}.txt") 
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt_text)
        return prompt_path

    def read_response(self, timestamp):
        response_file = os.path.join(RESPONSES_DIR, f"response_{timestamp}.txt")
        try:
            with open(response_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading response file: {e}")
            return None

class IconFinder:
    def __init__(self):
        self.logger = logging.getLogger('IconFinder')
        self.grid_visualizer = GridVisualizer()
        try:
            self.claude_interface = ClaudeInterface()
            self.logger.info("IconFinder initialized with Claude interface")
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude interface: {str(e)}")
            raise
        
    def analyze_screen(self, target_app):
        """Analyze the screen and get coordinates for a target"""
        try:
            self.logger.info(f"Starting screen analysis for target: {target_app}")
            timestamp = get_timestamp()
            attempt_dir = os.path.join(SCREENSHOTS_DIR, timestamp)
            os.makedirs(attempt_dir, exist_ok=True)
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            original_path = os.path.join(attempt_dir, "original.png")
            screenshot.save(original_path)
            self.logger.debug(f"Saved original screenshot to: {original_path}")
            
            # Create and save grid overlay
            grid_screenshot = self.grid_visualizer.create_grid_overlay(screenshot)
            grid_path = os.path.join(attempt_dir, "grid.png")
            grid_screenshot.save(grid_path)
            self.logger.debug(f"Saved grid overlay to: {grid_path}")
            
            # Get Claude's analysis
            self.logger.info("Getting Claude's analysis...")
            response, _ = self.claude_interface.analyze_screenshot(grid_path, target_app)
            
            # Parse coordinates
            if "COORDINATES:" in response:
                coords_line = [line for line in response.split('\n') if "COORDINATES:" in line][0]
                coords = coords_line.split("COORDINATES:")[1].strip().strip('"')
                self.logger.debug(f"Parsed coordinates: {coords}")
                
                if coords.lower() != "not found" and ',' in coords:
                    try:
                        x, y = map(int, coords.split(','))
                        
                        # Validate coordinates
                        screen_width, screen_height = pyautogui.size()
                        if 0 <= x <= screen_width and 0 <= y <= screen_height:
                            # Draw crosshair for verification
                            marked_screenshot = self.grid_visualizer.draw_crosshair(grid_screenshot, x, y)
                            marked_path = os.path.join(attempt_dir, "target.png")
                            marked_screenshot.save(marked_path)
                            self.logger.info(f"Found valid coordinates: ({x}, {y})")
                            return True, (x, y), marked_path
                        else:
                            self.logger.warning(f"Coordinates ({x}, {y}) out of bounds ({screen_width}x{screen_height})")
                            return False, None, grid_path
                    except ValueError as e:
                        self.logger.error(f"Failed to parse coordinates: {str(e)}")
                        return False, None, grid_path
                else:
                    self.logger.warning("Target not found in coordinates")
                    return False, None, grid_path
            else:
                self.logger.warning("No coordinates found in response")
                return False, None, grid_path
                
        except Exception as e:
            self.logger.error(f"Error in analyze_screen: {str(e)}")
            return False, None, None