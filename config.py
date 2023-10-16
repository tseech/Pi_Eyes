###########################################################
# Server and client settings
###########################################################
nats_server = "nats://10.4.4.2:4222"

###########################################################
# Server only settings
###########################################################

# Number of frame to send to the eyes each second
frames_per_second = 10

# Number of frames the gaze should linger when there are no detections
frames_to_linger = 10

# Size of image to analyze. The default is 500px wide so a multiplier of 1 will
# keep 500 px and a multiplier of 2 will make a 1000px image
resize_frame = False
resized_frame_width = 500

# Video source for tracking (0 will use built-in camera - great for testing)
video_source = 0
# Low res
# video_source = "rtsps://192.168.50.1:7441/pPskzjjqxw1pR6X3?enableSrtp"
# Med res
# video_source = "rtsps://192.168.50.1:7441/ioIIvm9z0MV2StG3?enableSrtp"
# High res
# video_source = "rtsps://192.168.50.1:7441/Kh8ZwIvGWpjwBwuE?enableSrtp"

# Select the types of detections to do
movement_detection = True
facial_detection = True
# Facial detection can be expensive, so allow it to be reduced to once per eye frame
facial_detection_once_per_frame = True

# Reverse tracking (used when projecting eyes from behind and not reversing the image)
reverse_tracking = False

###########################################################
# Client only settings
###########################################################
full_screen = True
display_width = 1280
display_height = 720
