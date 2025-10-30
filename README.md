# Multi-Camera Capture System

A robust Python-based system for capturing frames from multiple cameras with intelligent fallback capabilities. This system supports simultaneous capture from multiple cameras with configurable frame rates, priority-based camera selection, and automatic mock mode fallback when hardware cameras are unavailable. Uses OpenCV (headless) for video capture and Pillow for image processing, providing excellent cross-platform compatibility and lightweight performance.

## Key Features

- **Priority-based camera selection**: Tries specified cameras first, falls back to any available camera
- **Intelligent mock mode**: Generates random frames when no cameras are available
- **Cross-platform support**: Windows, Linux, macOS, and Jetson devices
- **Flexible configuration**: YAML config files with CLI override support
- **Organized output**: Separate folders for real camera captures and mock mode
- **Multi-threading**: Optimized single-camera mode and threaded multi-camera mode

## Package layout and usage

- `recorder/`: holds the actual package code.
- `examples/run.py`: shows how to use it programmatically as a library (imports `recorder`).
- `setup.py`: lets you run `pip install -e .` and then use both CLI-style module execution and library imports.

### Install (editable)

```bash
pip install -e .
```

### Programmatic usage (see `examples/run.py`)

```python
from recorder.camera import CameraCapture
from recorder.multi_camera import MultiCameraCapture
from recorder.utils import load_config, get_setting, find_available_camera_from_list

config = load_config("./recorder/config.yaml")
cameras = get_setting(None, config.get("cameras"), [0])
output_dir = get_setting(None, config.get("output_dir"), "./frames")
fps = int(get_setting(None, config.get("fps"), 30))
duration = get_setting(None, config.get("duration"), None)

if len(cameras) == 1:
    # Priority-based camera selection with mock mode fallback
    best_camera = find_available_camera_from_list(cameras)
    if best_camera is not None:
        CameraCapture(best_camera, output_dir, fps, use_mock_mode=True).run(duration)
    else:
        # No cameras available - use mock mode
        CameraCapture(cameras[0], output_dir, fps, use_mock_mode=True).run(duration)
else:
    MultiCameraCapture(cameras, output_dir, fps).run(duration)
```

Note: A legacy script (`camera_capture.py`) still exists for direct script usage, but the recommended interface is the package API and the `recorder` CLI documented below.

### Example configuration

An example YAML config is provided at `examples/config.yaml`:

```yaml
# Capture configuration
# cameras: List of camera IDs (priority order) - tries each in order, falls back to any available
# output_dir: Directory to save frames
# fps: Frames per second
# duration: Optional capture duration in seconds; omit or set null for continuous
cameras: [0]  # Try camera 0 first, fall back to any available camera
output_dir: ./frames
fps: 30
duration: null
```

### CLI usage (installed console script)

After `pip install -e .`, use the `recorder` command:

```bash
# Use config file (uses recorder/config.yaml by default)
recorder

# Use specific config file
recorder --config examples/config.yaml

# Override via CLI flags (priority-based selection)
recorder --cameras 0 1 --fps 25 --output ./captures --duration 60

# Simple single-camera example (tries camera 0, falls back to any available)
recorder --cameras 0 --output ./frames --fps 15

# Multiple cameras (each tries specified camera, falls back to available)
recorder --cameras 0 1 2 --output ./frames --fps 15

# List available cameras
recorder --list-cameras

# Test with non-existent camera (will use mock mode)
recorder --cameras 99
```

### Platform-specific camera handling

**Windows:**
- Use numeric camera indices like `0`, `1`, `2` (OpenCV standard)
- Run `--list-cameras` to see available camera indices
- Camera 0 is typically the default/built-in camera

**Linux/Jetson:**
- Use numeric camera IDs like `0`, `1`, `2`
- Cameras are typically `/dev/video0`, `/dev/video1`, etc.
- Jetson devices get optimized backend selection

## Camera Selection Behavior

The system uses **priority-based camera selection** with intelligent fallback:

1. **Try specified camera first**: If you specify `cameras: [1]`, it tries camera 1
2. **Fall back to any available**: If camera 1 doesn't exist, it tries camera 0, 2, 3, etc.
3. **Mock mode as last resort**: If no cameras exist, generates random frames

### Examples:

- `cameras: [1]` → Tries camera 1, falls back to camera 0 if available, uses mock if none
- `cameras: [0, 1, 2]` → Each slot tries its camera, falls back to any available
- `cameras: [99]` → Camera 99 doesn't exist, falls back to camera 0 or mock mode

## Output Structure

The system creates organized output directories:

```
./frames/
├── camera_0/          # Real camera 0 captures
│   └── camera_0_20251030_183345_123_no_user.jpg
├── camera_1/          # Real camera 1 captures  
│   └── camera_1_20251030_183346_456_no_user.jpg
└── mock_camera/       # Mock mode captures (when no cameras available)
    └── camera_99_20251030_183347_789_mocked_no_user.jpg
```

### File Naming Convention:
- **Real cameras**: `camera_{id}_{timestamp}_{user}.jpg`
- **Mock mode**: `camera_{id}_{timestamp}_mocked_{user}.jpg`
