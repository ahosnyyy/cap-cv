import time
import yaml
import cv2
import os
import platform
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_JETSON = os.path.exists("/etc/nv_tegra_release") if IS_LINUX else False


def _maintain_fps(loop_start_time: float, frame_interval: float) -> None:
    elapsed = time.time() - loop_start_time
    if elapsed < frame_interval:
        time.sleep(frame_interval - elapsed)


def should_stop(start_time: float, duration: Optional[int]) -> bool:
    return duration is not None and (time.time() - start_time) >= duration


def get_setting(cli_value, config_value, default):
    return cli_value if cli_value is not None else (config_value if config_value is not None else default)


def load_config(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def get_camera_device_path(camera_id) -> str:
    """Get the appropriate camera device path for OpenCV"""
    if IS_WINDOWS:
        # OpenCV on Windows uses integer indices
        if isinstance(camera_id, str):
            return "0"  # Default to first camera for string names
        else:
            return str(camera_id)
    elif IS_LINUX:
        if isinstance(camera_id, str):
            return f"/dev/video{camera_id}"
        else:
            return f"/dev/video{camera_id}"
    else:
        return str(camera_id)  # macOS uses integer indices


def get_platform_backend() -> str:
    """Return OpenCV backend info (for logging purposes)"""
    if IS_WINDOWS:
        return 'DirectShow'
    elif IS_LINUX:
        return 'V4L2'
    else:
        # macOS or others
        return 'AVFoundation'


def list_windows_cameras() -> List[int]:
    """List available Windows cameras using OpenCV"""
    available_cameras = []
    
    # Test camera indices 0-9
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
            cap.release()
        except:
            continue
    
    return available_cameras


def list_available_cameras() -> List:
    """List available camera devices based on platform"""
    available_cameras = []
    
    if IS_WINDOWS:
        # On Windows, list camera indices
        available_cameras = list_windows_cameras()
    elif IS_LINUX:
        # On Linux, check /dev/video* devices
        for i in range(10):
            device_path = f"/dev/video{i}"
            if os.path.exists(device_path):
                try:
                    cap = cv2.VideoCapture(device_path)
                    if cap.isOpened():
                        available_cameras.append(i)
                    cap.release()
                except:
                    continue
    else:
        # macOS or other platforms: test indices 0-9
        for i in range(10):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append(i)
                cap.release()
            except:
                continue
    
    return available_cameras


def resolve_windows_camera_name(camera_id) -> Optional[int]:
    """Best-effort: map a camera_id to a working OpenCV camera index."""
    if isinstance(camera_id, int):
        # Test if the integer camera ID works
        try:
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                cap.release()
                return camera_id
            cap.release()
        except:
            pass
    
    # If string or failed integer, try to find first available camera
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.release()
                return i
            cap.release()
        except:
            continue
    return None
