import cv2
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import logging
from PIL import Image
import platform
import os
from .utils import _maintain_fps, should_stop, get_camera_device_path, get_platform_backend, resolve_windows_camera_name

logger = logging.getLogger(__name__)

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_JETSON = os.path.exists("/etc/nv_tegra_release") if IS_LINUX else False


class CameraCapture:
    """Handles capture from a single camera using OpenCV"""

    def __init__(self, camera_id, output_dir: str, fps: int = 30, use_mock_mode: bool = False):
        # Store the original camera_id for OpenCV
        self.camera_id = camera_id
        # Create safe directory name from camera_id
        safe_camera_name = str(camera_id).replace(" ", "_").replace(":", "_")
        self.output_dir = Path(output_dir) / f"camera_{safe_camera_name}"
        self.fps = fps
        self.use_mock_mode = use_mock_mode
        self.is_running = False
        self.cap = None
        self.frame_count = 0
        # Mock mode fields
        self.mock_mode = False
        self.mock_width = 1280
        self.mock_height = 720

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized camera {camera_id} with output directory: {self.output_dir}")

    def _get_opencv_device_id(self) -> int:
        """Convert camera_id to OpenCV device ID"""
        if IS_WINDOWS:
            if isinstance(self.camera_id, str):
                # Try to resolve string camera names to indices
                resolved = resolve_windows_camera_name(self.camera_id)
                return resolved if resolved is not None else 0
            elif isinstance(self.camera_id, int):
                return self.camera_id
            else:
                return 0
        elif isinstance(self.camera_id, int):
            return self.camera_id
        else:
            return 0

    def _configure_opencv_capture(self, opts: Dict[str, str]):
        """Configure OpenCV capture properties"""
        if 'video_size' in opts:
            try:
                width, height = opts['video_size'].split('x')
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
            except:
                pass
        
        if 'framerate' in opts:
            try:
                self.cap.set(cv2.CAP_PROP_FPS, float(opts['framerate']))
            except:
                pass

    def start(self) -> bool:
        """Start camera capture"""
        try:
            # Get platform-specific backend
            input_format = get_platform_backend()
            device_path = get_camera_device_path(self.camera_id)

            logger.info(f"Platform: {platform.system()}, Jetson: {IS_JETSON}")
            logger.info(f"Using backend: {input_format}")

            # Get OpenCV device ID
            device_id = self._get_opencv_device_id()

            # Build a list of option attempts for better compatibility
            option_attempts: List[Dict[str, str]] = []
            base_options = self._get_format_options(input_format)

            if input_format == 'DirectShow':
                # Try progressively with different resolutions
                option_attempts = [
                    {},
                    {'framerate': base_options.get('framerate', '30')},
                    {'video_size': '640x480'},
                    {'video_size': '1280x720'},
                    {'video_size': '1920x1080'},
                    {'video_size': '1280x720', 'framerate': base_options.get('framerate', '30')},
                ]
            else:
                option_attempts = [base_options]

            last_error: Optional[Exception] = None
            for opts in option_attempts:
                try:
                    logger.debug(f"Opening with {input_format} device ID: {device_id}, options: {opts}")
                    self.cap = cv2.VideoCapture(device_id)
                    if not self.cap.isOpened():
                        raise Exception("Failed to open camera")
                    self._configure_opencv_capture(opts)
                    logger.info(f"Camera {self.camera_id} opened with format {input_format} and options {opts}")
                    self.is_running = True
                    return True
                except Exception as e:
                    last_error = e
                    if self.cap:
                        self.cap.release()
                        self.cap = None
                    continue
            logger.error(f"Failed to open camera {self.camera_id} with format {input_format}: {last_error}")
            # Enable mock mode if camera cannot be opened
            logger.warning("Falling back to mock mode: generating random frames")
            self.is_running = True
            if self.use_mock_mode:
                self.mock_mode = True
            else:
                return False
            # Try to parse desired video size from options if present
            try:
                size = self._get_format_options(input_format).get('video_size', '1280x720')
                w, h = size.split('x')
                self.mock_width = int(w)
                self.mock_height = int(h)
            except Exception:
                pass
            return True

        except Exception as e:
            logger.error(f"Error starting camera {self.camera_id}: {e}")
            return False

    def _get_input_url(self, input_format: str, device_path: str) -> str:
        """Get the input URL based on format and platform"""
        if input_format == 'v4l2':
            return device_path
        elif input_format == 'dshow':
            return device_path
        else:  # avfoundation or other
            return device_path

    def _get_format_options(self, input_format: str) -> Dict[str, str]:
        """Get format-specific options"""
        options = {
            'video_size': '1920x1080',
            'framerate': str(self.fps)
        }

        if input_format == 'dshow':
            options['video_size'] = '1920x1080'
        elif input_format == 'avfoundation':
            # avfoundation typically uses options like 'pixel_format'
            pass

        return options

    def stop(self):
        """Stop camera capture"""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info(f"Camera {self.camera_id} stopped")

    def capture_frame(self) -> Optional[Image.Image]:
        """Capture a single frame"""
        if not self.is_running:
            return None

        # Mock frame generation path
        if self.mock_mode:
            try:
                # Generate random RGB image using os.urandom to avoid numpy dependency
                num_bytes = self.mock_width * self.mock_height * 3
                random_bytes = os.urandom(num_bytes)
                pil_image = Image.frombytes('RGB', (self.mock_width, self.mock_height), random_bytes)
                return pil_image
            except Exception as e:
                logger.error(f"Failed to generate mock frame: {e}")
                return None

        try:
            # Capture frame using OpenCV
            ret, frame = self.cap.read()
            if ret:
                # Convert BGR to RGB for PIL compatibility
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                logger.debug(f"Captured frame from camera {self.camera_id}")
                return pil_image
        except Exception as e:
            logger.error(f"Failed to capture frame from camera {self.camera_id}: {e}")
        return None

    def save_frame(self, frame: Image.Image, user_name: str = "no_user") -> str:
        """Save frame with timestamp using Pillow"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        if self.mock_mode:
            filename = f"camera_{self.camera_id}_{timestamp}_mocked_{user_name}.jpg"
        else:
            filename = f"camera_{self.camera_id}_{timestamp}_{user_name}.jpg"
        filepath = self.output_dir / filename

        # Save PIL Image directly with high quality
        frame.save(str(filepath), 'JPEG', quality=95, optimize=True)
        self.frame_count += 1

        return str(filepath), self.mock_mode

    def capture_save_frame(self, user_name: str = "no_user") -> Optional[str]:
        """Capture a single frame and save it. Returns filepath if saved."""
        if not self.is_running:
            return None
        frame = self.capture_frame()
        if frame is None:
            return None
        return self.save_frame(frame, user_name)

    def run(self, duration: Optional[int] = None):
        """Run single camera capture loop"""
        if not self.start():
            logger.error("Failed to start camera")
            return

        logger.info("Using single camera mode (no threading)")
        frame_interval = 1.0 / self.fps
        start_time = time.time()

        try:
            if duration:
                logger.info(f"Capturing for {duration} seconds...")
            else:
                logger.info("Capturing continuously. Press Ctrl+C to stop...")

            while self.is_running:
                loop_start = time.time()

                filepath = self.capture_save_frame()
                if filepath:
                    logger.debug(f"Saved frame: {filepath}")

                # Check duration limit
                if should_stop(start_time, duration):
                    break

                # Maintain FPS
                _maintain_fps(loop_start, frame_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()
