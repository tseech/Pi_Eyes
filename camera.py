# Borrowed from https://stackoverflow.com/questions/51722319/skip-frames-and-seek-to-end-of-rtsp-stream-in-opencv
import threading
from threading import Lock
import cv2


# This class will start capturing video from a source and always make the newest frame available.
# This is useful when you always want the latest from and dropping frames is acceptable or needed.
class Camera:
    last_frame = None
    last_ready = None
    width = 0
    height = 0
    lock = Lock()

    def __init__(self, rtsp_link):
        # Start the video capture
        capture = cv2.VideoCapture(rtsp_link)
        # Create a thread to read frames from the video feed as they become available
        thread = threading.Thread(target=self.rtsp_cam_buffer, args=(capture,), name="rtsp_read_thread")
        thread.daemon = True
        # Start thread
        thread.start()

    def rtsp_cam_buffer(self, capture):
        while True:
            with self.lock:
                # Save the latest frame captured
                self.last_ready, self.last_frame = capture.read()
            # If the frame size has not been set, try to get it now
            if self.width == 0:
                self.width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
                self.height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def get_frame(self):
        if (self.last_ready is not None) and (self.last_frame is not None):
            return self.last_frame.copy()
        else:
            return None

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height
