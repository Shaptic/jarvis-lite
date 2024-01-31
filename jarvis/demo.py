import time

from picamera2 import Picamera2 as PiCam
from picamera2 import Preview
from libcamera import Transform

import cv2 as cv

picam = PiCam()
picam.configure(
  picam.create_preview_configuration(
    main={
      "format": "XRGB8888",
      "size": (1920, 1080),
    },
    transform=Transform(vflip=1)
  )
)
picam.start()

while True:
  im = picam.capture_array()
  cv.imshow("Camera Output", im)
  try:
    if cv.waitKey(1) == ord('q'):
      break
  except KeyboardInterrupt:
    break
