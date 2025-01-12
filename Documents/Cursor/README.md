# Icon Finder

A Python application that uses Claude Vision to locate and click on desktop icons and UI elements.

## Features

- Visual grid overlay for precise coordinate tracking
- Real-time icon/element detection using Claude Vision
- Interactive GUI with live feedback
- Click verification with visual markers
- Detailed logging system
- Edge-aware coordinate display

## Requirements

- Python 3.8+
- PyQt6
- Anthropic API key (for Claude Vision)
- Other dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Drew-source/icon_finder.git
cd icon_finder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

1. Run the GUI application:
```bash
python icon_finder/gui.py
```

2. Enter the name of the icon/element you want to find (e.g., "Chrome", "File Explorer")
3. Click "Find and Click" to start the detection
4. The application will:
   - Take a screenshot
   - Add a coordinate grid
   - Analyze using Claude Vision
   - Display results and click the target

## Project Structure

```
icon_finder/
├── data/
│   ├── screenshots/    # Screenshot storage
│   └── responses/      # Claude's responses
├── icon_finder/
│   ├── gui.py         # Main GUI application
│   └── icon_finder.py # Core functionality
├── prompts/           # Claude system prompts
├── logs/             # Application logs
└── .env              # Environment variables
```

## Features in Detail

- **Grid Visualization**: Red grid overlay with coordinate markers every 100 pixels
- **Target Marking**: Bright lime green crosshair with edge-aware coordinate display
- **Logging System**: Comprehensive logging with user and debug information
- **Response Analysis**: Full Claude Vision analysis display
- **Error Handling**: Robust error handling with informative messages

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 