#!/usr/bin/python

# Network crazy eyes : Server
#
# A remix of:
#
# Adafruit / Phillip Burgess (Paint Your Dragon)'s Animated Snake Eyes for Raspberry Pi
# https://learn.adafruit.com/animated-snake-eyes-bonnet-for-raspberry-pi/software-installation
# https://github.com/adafruit/Pi_Eyes
#
# Nathan Jennings / Real Python guide to Socket Programming in Python (Guide)
# https://realpython.com/python-sockets/#handling-multiple-connections
# https://github.com/realpython/materials/blob/master/python-sockets-tutorial/multiconn-server.py
#
# Adrian Rosebrock's motion detection tutorial
# https://www.pyimagesearch.com/2015/06/01/home-surveillance-and-motion-detection-with-the-raspberry-pi-python-and-opencv/

# Installing OpenCV:
# sudo apt-get install libhdf5-dev -y && sudo apt-get install libhdf5-serial-dev -y && sudo apt-get install libatlas-base-dev -y && sudo apt-get install libjasper-dev -y && sudo apt-get install libqtgui4 -y && sudo apt-get install libqt4-test -y
# pip3 install opencv-contrib-python
#

import math
import random
import time
import cv2
import imutils  # https://github.com/jrosebr1/imutils/
import asyncio
import nats
import json
import config
from camera import Camera
from detectors import FaceDetector
from detectors import MotionDetector


def find_closes_point(detections, cur_x, cur_y, analysis_frame_width_multiplier):
    distance = 999999
    new_x = 0
    new_y = 0
    new_w = 0
    new_h = 0
    for detection in detections:
        x = ((detection.x + (
                detection.w / 2)) / analysis_frame_width_multiplier - 320) * 0.093  # scale x to +/-30
        y = ((detection.y + (
                detection.h / 2)) / analysis_frame_width_multiplier - 240) * 0.093  # scale y to +/-30
        dist = math.dist((cur_x, cur_y), (x, y))
        if dist < distance:
            distance = dist
            new_x = detection.x
            new_y = detection.y
            new_w = detection.w
            new_h = detection.h
    return new_x, new_y, new_w, new_h


async def main():
    PUPIL_SMOOTH = 16  # If > 0, filter input from PUPIL_IN
    PUPIL_MIN = 0.0  # Lower analog range from PUPIL_IN
    PUPIL_MAX = 1.0  # Upper "

    startX = random.uniform(-30.0, 30.0)
    n = math.sqrt(900.0 - startX * startX)
    startY = random.uniform(-n, n)
    destX = startX
    destY = startY
    curX = startX
    curY = startY
    moveDuration = random.uniform(0.075, 0.175)
    holdDuration = random.uniform(0.1, 1.1)
    startTime = 0.0
    is_moving = False
    currentPupilScale = 0.5
    lidWeight = 0.0

    AUTOBLINK = True  # If True, eye blinks autonomously

    timeOfLastBlink = 0.0
    timeToNextBlink = 1.0
    blinkState = 0
    blinkDuration = 0.1
    blinkStartTime = 0
    blinkState = 0

    # Connect to the NATs server
    nc = await nats.connect(config.nats_server)

    # Create the video source to read from
    camera = Camera(config.video_source)

    # Create the detectors
    face_detector = FaceDetector()
    motion_detector = MotionDetector()

    ##########################
    # State tracking variables
    ##########################
    # Track the last time of th last frame sent to send at the configured frame rate
    last_frame_processed_time_ns = 0
    # Count frames since movement to provide make the eyes linger on the last thing seen
    frame_linger_count = 0
    # Track if faces should be detected because it is an expensive operation
    detect_faces = config.facial_detection
    # List of detections found since last frame was sent to eyes
    detections = list()

    #############################
    # Runtime calculated settings
    #############################
    # Value to multiply eyes X value to reverse left/right tracking
    x_multiplier = -1 if config.reverse_tracking else 1
    # Track the width multiplier for the frame to make eyes track accurately on different frame sizes
    # It will be set in code when the width is known
    analysis_frame_width_multiplier = 1

    try:
        while True:
            # Read a frame, detect motions, and accumulate the detections for processing
            frame = camera.get_frame()
            if frame is None:
                continue

            if config.resize_frame:
                analysis_frame_width_multiplier = config.resized_frame_width / 500
                frame = imutils.resize(frame, width=config.resized_frame_width)
            else:
                analysis_frame_width_multiplier = camera.get_width() / 500

            if config.movement_detection:
                motion_detections = motion_detector.detect(frame)
                detections += motion_detections

            if config.facial_detection and detect_faces:
                face_detections = face_detector.detect(frame)
                detections += face_detections
                if config.facial_detection_once_per_frame:
                    detect_faces = False

            # Only process the data to transmit at the requested frame rate
            if time.time_ns() - last_frame_processed_time_ns < 1 / config.frames_per_second * 1000000000:
                # Don't process the data yet
                continue

            detect_faces = True
            # Now process the data and reset the timer and detection accumulation
            last_frame_processed_time_ns = time.time_ns()
            detections_to_process = detections
            detections = list()

            # Check if there is any motion
            motion_detected = len(detections_to_process) > 0

            for detection in detections_to_process:
                cv2.rectangle(frame, (detection.x, detection.y),
                              (detection.x + detection.w, detection.y + detection.h), (0, 255, 0), 2)

            # display the image
            cv2.imshow('Motion Detection', frame)
            if motion_detected is not True:
                key = cv2.waitKey(1) & 0xFF
                # if the `r` key is pressed, refresh the average
                if key == ord("q"):
                    motion_detector.reset_avg()

            now = time.time()
            dt = now - startTime

            if motion_detected is not True and frame_linger_count < config.frames_to_linger:
                motion_detected = True
                frame_linger_count += 1
            elif motion_detected:
                frame_linger_count = 0

                # Motion detected to move eyes to center of motion
                # and shrink the pupil
                (x, y, w, h) = find_closes_point(detections_to_process, curX, curY, analysis_frame_width_multiplier)

                curX = ((x + (w / 2)) / analysis_frame_width_multiplier - 320) * 0.093  # scale x to +/-30
                curY = ((y + (h / 2)) / analysis_frame_width_multiplier - 240) * 0.093  # scale y to +/-30
                currentPupilScale = PUPIL_MIN

                for detection in detections_to_process:
                    cv2.rectangle(frame, (detection.x, detection.y),
                                  (detection.x + detection.w, detection.y + detection.h), (0, 255, 0), 2)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 0), 2)
                cv2.imshow('Motion Detection', frame)
                key = cv2.waitKey(1) & 0xFF
                # if the `r` key is pressed, refresh the average
                if key == ord("q"):
                    motion_detector.reset_avg()
            else:
                # Autonomous eye position
                if is_moving:
                    if dt <= moveDuration:
                        scale = (now - startTime) / moveDuration
                        # Ease in/out curve: 3*t^2-2*t^3
                        scale = 3.0 * scale * scale - 2.0 * scale * scale * scale
                        curX = startX + (destX - startX) * scale
                        curY = startY + (destY - startY) * scale
                    else:
                        startX = destX
                        startY = destY
                        curX = destX
                        curY = destY
                        holdDuration = random.uniform(0.15, 1.7)
                        startTime = now
                        is_moving = False
                else:
                    if dt >= holdDuration:
                        destX = random.uniform(-30.0, 30.0)
                        n = math.sqrt(900.0 - destX * destX)
                        destY = random.uniform(-n, n)
                        moveDuration = random.uniform(0.075, 0.175)
                        startTime = now
                        is_moving = True

                # Autonomous pupil size
                # Use sin to vary the pupil diameter from 50% to PUPIL_MAX over 10 seconds
                currentPupilScale = ((math.sin(2 * math.pi * (now % 10) / 10) / 4) + 0.5) * PUPIL_MAX

            # Blinking
            if AUTOBLINK and (now - timeOfLastBlink) >= timeToNextBlink:
                timeOfLastBlink = now
                duration = random.uniform(0.06, 0.12)
                if blinkState != 1:
                    blinkState = 1  # ENBLINK
                    blinkStartTime = now
                    blinkDuration = duration
                if (motion_detected):
                    timeToNextBlink = random.uniform(4.0, 6.0)
                else:
                    timeToNextBlink = duration * 3 + random.uniform(0.0, 4.0)

            if blinkState:  # Eye currently winking/blinking?
                # Check if blink time has elapsed...
                if (now - blinkStartTime) >= blinkDuration:
                    # Increment blink state
                    blinkState += 1
                    if blinkState > 2:
                        blinkState = 0  # NOBLINK
                    else:
                        blinkDuration *= 2.0
                        blinkStartTime = now

            if blinkState:
                lidWeight = (now - blinkStartTime) / blinkDuration
                if lidWeight > 1.0: lidWeight = 1.0
                if blinkState == 2: lidWeight = 1.0 - lidWeight
            else:
                lidWeight = 0.0

            shared = {"curX": curX * x_multiplier, "curY": curY, "pupil": currentPupilScale, "lid": lidWeight,
                      "blink": blinkState}
            data = bytes(json.dumps(shared), "utf-8")
            print(data)
            await nc.publish("eyes", data)
            await nc.flush(timeout=1)

    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")

    finally:
        cv2.destroyAllWindows()
        await nc.drain()
        await nc.close()


if __name__ == '__main__':
    asyncio.run(main())
