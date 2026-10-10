"""Pure, host-testable state machine. No motor output on invalid input."""
import math

def level(samples):
    if len(samples) < 32 or any(not isinstance(x,(int,float)) or not math.isfinite(x) or not 0 <= x <= 65535 for x in samples):
        return None
    mean=sum(samples)/len(samples)
    # Bias / clipping checks are a guard, not a guaranteed sensor disconnect test.
    if not 6000 < mean < 59000 or min(samples)<200 or max(samples)>65300:
        return None
    return math.sqrt(sum((x-mean)**2 for x in samples)/len(samples))

class Controller:
    def __init__(self,on=1000,off=700,cap_ms=5000,allow_continuous=False):
        if not 0 <= off < on < 20000 or not (500 <= cap_ms <= 10000 or cap_ms==0 and allow_continuous is True):
            raise ValueError('Bad commissioning limits')
        self.on,self.off,self.cap=on,off,cap_ms
        self.armed=False;self.driving=False;self.locked=False
        self.run_start=None;self.quiet_seen=False

    def arm(self):
        self.armed=True;self.driving=False;self.locked=False
        self.run_start=None;self.quiet_seen=False

    def stop(self):
        self.armed=False;self.driving=False;self.run_start=None;self.quiet_seen=False

    def update(self,rms,now_ms,age_ms=0):
        if rms is None or not math.isfinite(rms) or rms<0 or not 0<=age_ms<=250:
            self.stop();return False,'传感器/样本异常；重新检查并 ARM'
        if not self.armed: return False,'未解锁，按 ARM'
        if rms<=self.off:
            self.driving=False;self.run_start=None;self.locked=False;self.quiet_seen=True
            return False,'安静，停车'
        if not self.quiet_seen: return False,'先保持安静，再发声'
        if self.locked: return False,'连续运行保护；先安静再重试'
        if self.driving and (now_ms-self.run_start<0 or self.cap and now_ms-self.run_start>=self.cap):
            self.driving=False;self.locked=True;return False,'达到试车时限，停车'
        if rms>self.on and not self.driving:
            self.driving=True;self.run_start=now_ms
        return self.driving, '响度超过门槛' if self.driving else '未达到启动门槛'

