"""Romeo mini DFR1063 ESP32-C3 + DFR0034 V2. NOT v1 pin-compatible.
Relative analogue intensity counts, not calibrated dB SPL. Lift wheels first.
"""
MIC_PIN, ARM_PIN = 3, 6
DIR_L, PWM_L = 1, 0
DIR_R, PWM_R = 10, 2
THRESHOLD_ON, THRESHOLD_OFF = 5000, 3000  # EXAMPLES: measure your sensor first
PWM_DUTY = 0.45
PROFILE = 'commissioning'
HARDWARE_CHECKED = False
LEFT_TRIM, RIGHT_TRIM = 1.0, 1.0
LEFT_FORWARD, RIGHT_FORWARD = 1, 0
MAX_RUN_MS = 5000
SAMPLE_COUNT, SAMPLE_MS = 32, 2
QUIET_SETTLE_MS = 250
DRIVE_MS = 160
