import sys
import os
import traceback
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QScrollArea, QTextEdit, QSplitter, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from datetime import datetime
import pyautogui

# Import from icon_finder package
from icon_finder import IconFinder

class ClickableLabel(QLabel):
    """A label that can be clicked to show full size image"""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 300)
        self.current_image_path = None
        
    def mousePressEvent(self, event):
        if self.current_image_path and os.path.exists(self.current_image_path):
            os.startfile(self.current_image_path)
            
    def setImage(self, image_path):
        """Set image and store path for click handling"""
        self.current_image_path = image_path
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled_pixmap)
            
    def resizeEvent(self, event):
        """Rescale image when label is resized"""
        if self.current_image_path and os.path.exists(self.current_image_path):
            self.setImage(self.current_image_path)
        super().resizeEvent(event)

class IconFinderWorker(QThread):
    finished = pyqtSignal(bool, str, str, str)  # Success flag, message, image path, Claude's response
    
    def __init__(self, target_app, icon_finder):
        super().__init__()
        self.target_app = target_app
        self.icon_finder = icon_finder
        self.logger = logging.getLogger('IconFinder')
        
    def run(self):
        try:
            # Get coordinates from IconFinder
            success, coords, image_path = self.icon_finder.analyze_screen(self.target_app)
            
            if success and coords:
                try:
                    x, y = coords
                    
                    # Validate coordinates are within screen bounds
                    screen_width, screen_height = pyautogui.size()
                    if not (0 <= x < screen_width and 0 <= y < screen_height):
                        error_msg = f"Coordinates ({x}, {y}) are outside screen bounds ({screen_width}x{screen_height})"
                        self.finished.emit(False, error_msg, image_path if image_path else "", error_msg)
                        return
                    
                    # Get Claude's response from the response file
                    claude_response = "No analysis available"
                    
                    if image_path:
                        # Extract timestamp from image path
                        timestamp = os.path.basename(os.path.dirname(image_path))
                        response_path = os.path.join("data", "responses", f"response_{timestamp}.txt")
                        
                        if os.path.exists(response_path):
                            try:
                                with open(response_path, 'r', encoding='utf-8') as f:
                                    claude_response = f.read()
                                    if not claude_response.strip():
                                        claude_response = "Analysis was empty"
                            except Exception as e:
                                claude_response = f"Error reading response file: {str(e)}"
                        else:
                            claude_response = f"Response file not found at: {response_path}"
                    
                    # Perform click in the GUI thread
                    try:
                        pyautogui.click(x, y)
                        self.finished.emit(True, f"Clicked at ({x}, {y})", image_path, claude_response)
                    except Exception as click_error:
                        error_msg = f"Failed to click at ({x}, {y}): {str(click_error)}"
                        self.finished.emit(False, error_msg, image_path, claude_response)
                        
                except Exception as e:
                    error_msg = f"Error processing coordinates: {str(e)}\n{traceback.format_exc()}"
                    self.finished.emit(False, error_msg, image_path if image_path else "", error_msg)
            else:
                error_msg = "Could not find target or get valid coordinates"
                self.finished.emit(False, error_msg, image_path if image_path else "", error_msg)
        except Exception as e:
            error_msg = f"Error in worker thread: {str(e)}\n{traceback.format_exc()}"
            self.finished.emit(False, error_msg, "", error_msg)

class IconFinderGUI(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            self.setWindowTitle("Icon Finder")
            self.setGeometry(100, 100, 1200, 800)
            
            # Set up error logging first
            self.setup_logging()
            self.logger.info("Starting Icon Finder GUI...")
            
            # Initialize core functionality
            try:
                self.icon_finder = IconFinder()
                self.logger.info("IconFinder initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize IconFinder: {str(e)}")
                self.logger.debug(f"IconFinder initialization traceback: {traceback.format_exc()}")
                raise
            
            self.worker = None
            
            # Create main widget and layout
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            layout = QVBoxLayout(main_widget)
            
            # Create input section
            input_layout = QHBoxLayout()
            
            self.target_input = QLineEdit()
            self.target_input.setPlaceholderText("Enter target to click (e.g., 'Chrome')")
            input_layout.addWidget(self.target_input)
            
            self.find_button = QPushButton("Find and Click")
            self.find_button.clicked.connect(self.start_icon_finder)
            input_layout.addWidget(self.find_button)
            
            layout.addLayout(input_layout)
            
            # Create splitter for main content
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Left side: Tabbed view for logs
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            
            # Create tab widget for different logs
            self.tab_widget = QTabWidget()
            
            # User log tab
            user_log_widget = QWidget()
            user_log_layout = QVBoxLayout(user_log_widget)
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            user_log_layout.addWidget(self.log_text)
            self.tab_widget.addTab(user_log_widget, "User Log")
            
            # Debug log tab
            debug_log_widget = QWidget()
            debug_log_layout = QVBoxLayout(debug_log_widget)
            self.debug_log_text = QTextEdit()
            self.debug_log_text.setReadOnly(True)
            debug_log_layout.addWidget(self.debug_log_text)
            self.tab_widget.addTab(debug_log_widget, "Debug Log")
            
            # Claude's response tab
            claude_widget = QWidget()
            claude_layout = QVBoxLayout(claude_widget)
            self.claude_text = QTextEdit()
            self.claude_text.setReadOnly(True)
            claude_layout.addWidget(self.claude_text)
            self.tab_widget.addTab(claude_widget, "Claude's Analysis")
            
            left_layout.addWidget(self.tab_widget)
            splitter.addWidget(left_widget)
            
            # Right side: Screenshot
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            
            preview_label = QLabel("Screenshot with Grid (click to view full size)")
            right_layout.addWidget(preview_label)
            
            self.image_scroll = QScrollArea()
            self.image_scroll.setWidgetResizable(True)
            self.image_label = ClickableLabel()
            self.image_scroll.setWidget(self.image_label)
            right_layout.addWidget(self.image_scroll)
            
            splitter.addWidget(right_widget)
            
            # Add splitter to main layout
            layout.addWidget(splitter)
            
            # Set initial splitter sizes (40% left, 60% right)
            splitter.setSizes([400, 600])
            
            self.logger.info("GUI initialization complete")
            
        except Exception as e:
            # Log any initialization errors
            if hasattr(self, 'logger'):
                self.logger.error(f"Error during GUI initialization: {str(e)}")
                self.logger.debug(f"Initialization traceback: {traceback.format_exc()}")
            else:
                print(f"Failed to initialize logging: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
            raise  # Re-raise the exception to show the error
        
    def setup_logging(self):
        """Set up logging configuration"""
        self.logger = logging.getLogger('IconFinder')
        self.logger.setLevel(logging.DEBUG)
        
        try:
            # Use logs directory in project root
            log_dir = 'logs'  # Directly use logs folder in project root
            os.makedirs(log_dir, exist_ok=True)
            
            # Create a file handler that writes to a log file
            self.log_file = os.path.join(log_dir, 'icon_finder.log')
            print(f"Log file will be created at: {self.log_file}")
            
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Create a custom handler that writes to our debug log widget
            class QTextEditHandler(logging.Handler):
                def __init__(self, widget):
                    super().__init__()
                    self.widget = widget
                    
                def emit(self, record):
                    msg = self.format(record)
                    self.widget.append(msg)
            
            # Create handlers
            self.debug_handler = None  # Will be set after debug_log_text is created
            
            # Create formatters
            debug_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            
            # We'll set up the handler after debug_log_text is created
            def setup_debug_handler(self):
                if hasattr(self, 'debug_log_text') and not self.debug_handler:
                    self.debug_handler = QTextEditHandler(self.debug_log_text)
                    self.debug_handler.setFormatter(debug_formatter)
                    self.logger.addHandler(self.debug_handler)
            
            # Store the setup function to call later
            self._setup_debug_handler = setup_debug_handler
            
            self.logger.info("Logging initialized. Log file: %s", self.log_file)
            
        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise
        
    def get_log_file_path(self):
        """Return the absolute path to the log file"""
        if hasattr(self, 'log_file'):
            return os.path.abspath(self.log_file)
        return None
        
    def showEvent(self, event):
        """Called when the window is shown"""
        super().showEvent(event)
        # Set up debug handler now that all widgets are created
        self._setup_debug_handler(self)
        
    def start_icon_finder(self):
        """Start the icon finder process"""
        target = self.target_input.text().strip()
        if not target:
            self.add_log("Please enter a target")
            return
            
        try:
            # Disable button while processing
            self.find_button.setEnabled(False)
            self.add_log(f"Looking for {target}...")
            
            # Create and start worker thread
            self.worker = IconFinderWorker(target, self.icon_finder)
            self.worker.finished.connect(self.process_complete)
            self.worker.start()
            
        except Exception as e:
            self.logger.error(f"Error starting icon finder: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            self.add_log(f"Error: {str(e)}")
            self.find_button.setEnabled(True)
        
    def process_complete(self, success, message, image_path, claude_response):
        """Handle process completion"""
        try:
            self.add_log(message)
            self.find_button.setEnabled(True)
            
            # Update image preview if available
            if image_path and os.path.exists(image_path):
                self.image_label.setImage(image_path)
                self.logger.debug(f"Updated image preview: {image_path}")
            else:
                self.logger.warning(f"Image path not found: {image_path}")
            
            # Update Claude's response
            if claude_response:
                self.claude_text.setText(claude_response)
                self.logger.debug(f"Updated Claude's response: {claude_response[:100]}...")  # Log first 100 chars
            else:
                self.logger.warning("No Claude response received")
                self.claude_text.setText("No analysis available")
            
            self.worker = None
            
        except Exception as e:
            self.logger.error(f"Error in process_complete: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            self.add_log(f"Error completing process: {str(e)}")
        
    def add_log(self, message):
        """Add a message to the log"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}"
            self.log_text.append(log_message)
            self.logger.info(message)
            
        except Exception as e:
            self.logger.error(f"Error adding to log: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")

def main():
    app = QApplication(sys.argv)
    window = IconFinderGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 