#
# SuperDrive
# a live processing capable, clean(-ish) implementation of lane &
# path detection based on comma.ai's SuperCombo neural network model
#

import cv2
import pathlib
import matplotlib
import numpy as np
import tensorflow as tf
from parser import parser
import matplotlib.pyplot as plt
from undistort.undistort import undistort

# ============================================================================ #

# Configure capture here
CAMERA_DEVICE = "test.m4v"

# ============================================================================ #

# Initialize undistort
undist = undistort(frame_width=560, frame_height=315)

# Initialize OpenCV capture and set basic parameters
cap = cv2.VideoCapture(CAMERA_DEVICE)
cap.set(3, 1280)
cap.set(4, 720)
cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)

# Load Keras model for lane detection
lanedetector = tf.keras.models.load_model("supercombo.keras")

# We need a place to keep two separate consecutive image frames
# since that's what SuperCombo uses
fr0 = np.zeros((384,512), dtype=np.uint8)
fr1 = np.zeros((384,512), dtype=np.uint8)

# SuperCombo requires a feedback of state after each prediction
# (to improve accuracy?) and also requires a "desire" input to the network,
# so we'll allocate some space for those, too
state = np.zeros((1,512))
desire = np.zeros((1,8))

# Read frame
while(True):
    ret, frame = cap.read()

    # Resize incoming frame to smaller width (to save resource in undistortion)
    frame = cv2.resize(frame, (560, 315))

    # Undistort incoming frame
    # For those without autopilot-common, this is standard OpenCV undistortion
    # using a calibration matrix. In this case, a Logitech C920 is used. Just
    # perform chessboard calibration to get the matrices!
    frame = undist.frame(frame)

    # Crop the edges out and try to get to (512,256), since that's what
    # the SuperCombo model uses. Note that this is skewed a bit more
    # to the sky, since my camera can "see" the hood and that probably won't
    # help us in the task of lane detection, so we crop that out
    frame = frame[14:270,24:536]
    cv2.imshow("Undistorted", frame)

    # Then we want to convert this to YUV
    frameYUV = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)

    # We want to push our image in fr1 to fr0, and replace fr1 with
    # the current frame (to feed into the network)
    fr0 = fr1
    fr1 = frameYUV

    # SuperCombo input shape is (12, 128, 256): two consecutive images
    # in YUV space. We concatenate fr0 and fr1 together to get to that
    networkInput = np.concatenate((fr0, fr1))

    # We then want to reshape this into the shape the network requires
    networkInput = networkInput.reshape((1, 12, 128, 256))

    # Convert network input to float32 and normalize (TODO: why?)
    #networkInput = networkInput.astype(np.float32) / 128.0 - 1.0

    # Build actual input combination
    input = [networkInput, desire, state]

    # Then, we can run the prediction!
    # TODO: this is somehow very slow(?)
    networkOutput = lanedetector.predict(input)

    # Parse output and refeed state
    parsed = parser(networkOutput)
    state = networkOutput[-1]

    # Draw plots
    if(True):
        plt.clf()
        plt.title("Lane/Path Detection")
        plt.plot(parsed["lll"][0], range(0,192), "b-", linewidth=1)
        plt.plot(parsed["rll"][0], range(0, 192), "r-", linewidth=1)
        plt.plot(parsed["path"][0], range(0, 192), "g-", linewidth=1)
        plt.gca().invert_xaxis()
        plt.pause(0.001)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break