"""ECHO F1 v1; ESP32-DevKitC V4 (WROOM-32E), DFRobot DRI0044 only.
Relative AC RMS ADC counts, NOT calibrated dB SPL. Start with wheels lifted.
"""
MIC_PIN = 34
ARM_PIN = 32       # normally-open button to GND, internal pull-up
DIR_L, PWM_L = 25, 26
DIR_R, PWM_R = 27, 14
THRESHOLD_ON = 1000  # read_u16 AC RMS counts: tune from serial printout
THRESHOLD_OFF = 700
PWM_DUTY = 0.45      # low-speed commissioning; do not blindly increase
PROFILE = 'commissioning'
HARDWARE_CHECKED = False  # change only after completing the physical checklist
LEFT_TRIM = 1.0
RIGHT_TRIM = 1.0
LEFT_FORWARD, RIGHT_FORWARD = 1, 0  # mirror-mounted motors; verify wheels lifted
MAX_RUN_MS = 5000    # commissioning cap; requires quiet before next run
SAMPLE_COUNT = 160
SAMPLE_US = 250      # roughly 4 kHz, nominal 40 ms observation
QUIET_SETTLE_MS = 90 # PWM is off before EVERY observation to reduce self-triggering
DRIVE_MS = 160       # periodic quiet sampling introduces intentional short pauses

