"""MicroPython ESP32. User must install official ESP32_GENERIC firmware first.
Wi-Fi/Bluetooth unused. Battery disconnected whenever USB is attached.
"""
from machine import Pin, ADC, PWM, WDT
import time
import network
import config as C
from controller import Controller, level

for iface in (network.STA_IF,network.AP_IF): network.WLAN(iface).active(False)
for name in ('PWM_DUTY','LEFT_TRIM','RIGHT_TRIM'):
    value=getattr(C,name)
    if not isinstance(value,(int,float)) or not 0 < value <= 1: raise ValueError(name)
continuous=C.PROFILE=='continuous_while_loud'
if C.PROFILE not in ('commissioning','continuous_while_loud'): raise ValueError('Unknown profile')
if continuous and C.HARDWARE_CHECKED is not True: raise ValueError('Complete physical checklist before continuous mode')
if C.PWM_DUTY>(0.8 if continuous else 0.5): raise ValueError('PWM exceeds selected profile limit')
dir_l=Pin(C.DIR_L,Pin.OUT,value=0);dir_r=Pin(C.DIR_R,Pin.OUT,value=0)
pwm_l=PWM(Pin(C.PWM_L,Pin.OUT,value=0),freq=20000,duty=0)
pwm_r=PWM(Pin(C.PWM_R,Pin.OUT,value=0),freq=20000,duty=0)
arm=Pin(C.ARM_PIN,Pin.IN,Pin.PULL_UP)
mic=ADC(Pin(C.MIC_PIN));mic.atten(ADC.ATTN_11DB)
state=Controller(C.THRESHOLD_ON,C.THRESHOLD_OFF,0 if continuous else C.MAX_RUN_MS,continuous)
watchdog=WDT(timeout=2000)
released=False;last_button=1;epoch=time.ticks_ms();last_press=epoch

def stop_motors():
    pwm_l.duty(0);pwm_r.duty(0)

def button():
    global released,last_button,last_press
    value=arm.value();now=time.ticks_ms()
    if value==1: released=True
    if value==0 and last_button==1 and released and time.ticks_diff(now,last_press)>250:
        last_press=now;released=False
        if state.armed:state.stop();stop_motors()
        else:state.arm()
    last_button=value

try:
    print('ECHO F1: 相对响度，不是 dB SPL。先抬轮；按 ARM，保持安静，再发声。')
    while True:
        stop_motors()                 # never measure while intentionally driving
        time.sleep_ms(C.QUIET_SETTLE_MS)
        button()
        samples=[]
        for _ in range(C.SAMPLE_COUNT):
            samples.append(mic.read_u16());time.sleep_us(C.SAMPLE_US)
        rms=level(samples)
        drive,reason=state.update(rms,time.ticks_diff(time.ticks_ms(),epoch))
        print('RMS=',round(rms,1) if rms is not None else 'FAULT','ARM=',state.armed,reason)
        if drive:
            dir_l.value(C.LEFT_FORWARD);dir_r.value(C.RIGHT_FORWARD)
            pwm_l.duty(round(1023*C.PWM_DUTY*C.LEFT_TRIM));pwm_r.duty(round(1023*C.PWM_DUTY*C.RIGHT_TRIM))
        start=time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(),start)<C.DRIVE_MS:
            button()
            if not state.armed:stop_motors()
            time.sleep_ms(10)
        watchdog.feed()
except BaseException:
    stop_motors()
    raise
finally:
    stop_motors();pwm_l.deinit();pwm_r.deinit()
    Pin(C.PWM_L,Pin.OUT,value=0);Pin(C.PWM_R,Pin.OUT,value=0)

