# Image to Text Conversion Protocol

## 1. Grid Reading Pattern
- START: Top-left (0,0)
- DIRECTION: Left to right, top to bottom
- FORMAT: GRID[x,y]: <content_description>

## 2. Content Description Standards
### UI Elements
- Format: [type][state][content]
- Example: "GRID[x,y]: [button][active][file explorer]"

### Text Elements
- Format: [style][content][context]
- Example: "GRID[x,y]: [editor_text]['application-name'][input field]"

### Icons
- Format: [shape][colors][identifier]
- Example: "GRID[x,y]: [shape][color-scheme][icon type]"

## 3. Coordinate Calculation Rules
- Grid lines follow a range pattern (e.g., "300" = END of 200s range)
- Column position = ((column_number - 1) × 100) + offset
- Example: For any column N, position = ((N-1)×100) + offset

## 4. Validation Steps
1. Convert image to text grid
2. Identify target in grid
3. Calculate precise coordinates
4. Verify against common ranges

## 5. Common Element Patterns
### Taskbar Icons
- Format: GRID[x,y]: [icon_description]
- Range: Follows standard grid system
- Common positions: System elements, followed by pinned apps

### Window Elements
- Title bars: Near top of window
- Content area: Main window space
- Status bars: Bottom of window

### System Tray
- Range: Rightmost section of taskbar
- Format: GRID[x,y]: [icon][state][tooltip]

## 6. Reading Example
```
GRID[x1,y]: [square][white][start menu]
GRID[x2,y]: [rectangular][gray][search]
GRID[x3,y]: [circular][color-scheme][application]
GRID[x4,y]: [square][color][application]
...
``` 