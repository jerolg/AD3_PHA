from ctypes import c_int

# Instrument States
DwfStateReady = 0
DwfStateConfig = 1
DwfStatePrefill = 3
DwfStateArmed = 6
DwfStateWait = 7
DwfStateTriggered = 8
DwfStateRunning = 4
DwfStateDone = 2  # Critical for confirming capture

# Trigger Sources
trigsrcNone = c_int(0)
trigsrcDetectorAnalogIn = c_int(3)

# Acquisition Modes
acqmodeSingle = c_int(1)

# Trigger Slopes
slopeRising = c_int(0)
slopeFalling = c_int(1)