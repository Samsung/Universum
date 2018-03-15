import evdev
dev = evdev.InputDevice('/dev/input/event6')



import time
while True:
  try:
    for event in dev.read():
      print event
  except:
    time.sleep(.5)
