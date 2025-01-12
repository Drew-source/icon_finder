# Coordinate Reading Guide

## Fundamental Concept
The screen uses a coordinate system where:
- X increases from left to right (0 to 2560)
- Y increases from top to bottom (0 to 1440)
- Origin (0,0) is at top-left corner
- Grid lines are spaced 100 pixels apart

## Precise Coordinate Reading
1. Find nearest grid lines:
   - Count major grid lines (100px)
   - Estimate minor divisions (25px)
   - Use crosshair markers as reference

2. Common Ranges:
   - Taskbar: Y ≈ 1415
   - Window title bars: Y ≈ 75
   - Desktop icons: X < 500
   - System tray: X > 2000

## Auto-Correction Strategy
1. When target is missed:
   - Note current click position (red crosshair)
   - Compare to previous attempts (yellow crosshairs)
   - Determine direction and distance needed

2. Movement Guidelines:
   - Far (>200px): Move 200-300 pixels
   - Medium (100-200px): Move 100-150 pixels
   - Close (50-100px): Move 50-75 pixels
   - Very close (<50px): Move 10-20 pixels

3. Direction Analysis:
   - If too far right: Decrease X
   - If too far left: Increase X
   - If too far down: Decrease Y
   - If too far up: Increase Y

## Sequence Context
1. Consider target state:
   - Is window/app already open?
   - Are we clicking same region?
   - Has window position changed?

2. Adjust for changes:
   - Window movements
   - New elements appearing
   - UI state changes

## Validation Method
1. Before clicking:
   - Check coordinates are within screen
   - Verify against common ranges
   - Consider sequence context

2. After clicking:
   - Verify visual changes
   - Check for success indicators
   - Prepare for next step

## Common Mistakes to Avoid
1. Being too conservative in corrections
2. Ignoring previous attempt patterns
3. Not considering sequence context
4. Missing common element locations
5. Forgetting to verify success 