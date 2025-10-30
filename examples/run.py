import argparse
import logging
from pathlib import Path
from recorder.camera import CameraCapture
from recorder.multi_camera import MultiCameraCapture
from recorder.utils import load_config, get_setting, find_available_camera_from_list

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Multi-Camera Capture System")
    parser.add_argument("--config", type=str, default="./examples/config.yaml", help="Path to YAML config")
    parser.add_argument("--cameras", nargs="+", type=int, default=None, help="Camera IDs")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--fps", type=int, default=None, help="Frames per second")
    parser.add_argument("--duration", type=int, default=None, help="Duration in seconds")
    args = parser.parse_args()

    config_data = load_config(args.config)

    effective_cameras = get_setting(args.cameras, config_data.get("cameras"), [0])
    effective_output = get_setting(args.output, config_data.get("output_dir"), "./frames")
    effective_fps = int(get_setting(args.fps, config_data.get("fps"), 30))
    effective_duration = get_setting(args.duration, config_data.get("duration"), None)

    Path(effective_output).mkdir(parents=True, exist_ok=True)

    if len(effective_cameras) == 1:
        # Single camera mode - use priority-based selection
        best_camera = find_available_camera_from_list(effective_cameras)
        if best_camera is not None:
            logger.info(f"Using camera {best_camera} for requested camera {effective_cameras[0]}")
            camera = CameraCapture(best_camera, effective_output, effective_fps, use_mock_mode=True)
            camera.run(effective_duration)
        else:
            logger.error("No cameras available - falling back to mock mode")
            camera = CameraCapture(effective_cameras[0], effective_output, effective_fps, use_mock_mode=True)
            camera.run(effective_duration)
    else:
        system = MultiCameraCapture(effective_cameras, effective_output, effective_fps)
        system.run(effective_duration)

if __name__ == "__main__":
    main()