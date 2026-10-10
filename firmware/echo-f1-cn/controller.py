"""Host-testable safety state and envelope intensity, without hardware imports."""
import math

def level(samples):
    if len(samples) < 16 or any(type(x) not in (int,float) or not math.isfinite(x) or not 0 <= x <= 65535 for x in samples):
        return None
    mean=sum(samples)/len(samples)
    # DFR0034 outputs intensity. Removing DC and computing AC RMS would suppress
    # a sustained loud input. Rail clipping is a guard, not full unplug detection.
    if mean < 10 or mean > 64000 or max(samples) > 65400:
        return None
    return mean

class Controller:
    def __init__(self,on=5000,off=3000,cap_ms=5000,allow_continuous=False):
        if not all(type(x) in (int,float) and math.isfinite(x) for x in [on,off,cap_ms]):
            raise ValueError('Non-finite limits')
        if not 0 <= off < on < 64000 or not (500 <= cap_ms <= 10000 or cap_ms==0 and allow_continuous is True):
            raise ValueError('Bad commissioning limits')
        self.on,self.off,self.cap=on,off,cap_ms
        self.armed=False;self.driving=False;self.locked=False
        self.run_start=None;self.quiet_seen=False;self.last_now=None

    def arm(self):
        self.armed=True;self.driving=False;self.locked=False
        self.run_start=None;self.quiet_seen=False;self.last_now=None

    def stop(self):
        self.armed=False;self.driving=False;self.run_start=None;self.quiet_seen=False

    def update(self,intensity,now_ms,age_ms=0):
        if intensity is None or not isinstance(intensity,(int,float)) or not math.isfinite(intensity) or not 0<=intensity<=65535 or not isinstance(now_ms,(int,float)) or not math.isfinite(now_ms) or not 0<=age_ms<=250 or self.last_now is not None and now_ms<self.last_now:
            self.stop();return False,'FAULT: check sensor/time, then re-arm'
        self.last_now=now_ms
        if not self.armed:return False,'DISARMED'
        if intensity<=self.off:
            self.driving=False;self.run_start=None;self.locked=False;self.quiet_seen=True
            return False,'QUIET'
        if not self.quiet_seen:return False,'WAIT_FOR_QUIET'
        if self.locked:return False,'TIMEOUT_WAIT_FOR_QUIET'
        if self.driving and self.cap and now_ms-self.run_start>=self.cap:
            self.driving=False;self.locked=True;return False,'TIMEOUT'
        if intensity>self.on and not self.driving:
            self.driving=True;self.run_start=now_ms
        return self.driving,'LOUD' if self.driving else 'BELOW_THRESHOLD'
