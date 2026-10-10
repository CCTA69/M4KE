import unittest
from controller import Controller, level
import config as C

class Tests(unittest.TestCase):
    def test_intensity_is_not_ac_rms(self):self.assertEqual(level([9000]*32),9000)
    def test_invalid_and_rail(self):
        for x in [[],[100]*8,[0]*32,[65535]*32,[float('nan')]*32,[-1]*32]:self.assertIsNone(level(x))
    def test_arm_quiet_loud_stop(self):
        c=Controller();self.assertFalse(c.update(9000,0)[0]);c.arm()
        self.assertFalse(c.update(9000,1)[0]);self.assertFalse(c.update(1000,2)[0])
        self.assertTrue(c.update(9000,3)[0]);self.assertTrue(c.update(4000,4)[0])
        self.assertFalse(c.update(1000,5)[0])
    def test_timeout_and_rearm(self):
        c=Controller();c.arm();c.update(1000,0);c.update(9000,1)
        self.assertFalse(c.update(9000,5001)[0]);self.assertFalse(c.update(9000,5002)[0])
        c.update(1000,5003);self.assertTrue(c.update(9000,5004)[0])
    def test_fault_disarms(self):
        for value,age in [(None,0),(float('nan'),0),(9000,251)]:
            c=Controller();c.arm();c.update(1000,0);c.update(9000,1)
            self.assertFalse(c.update(value,2,age)[0]);self.assertFalse(c.armed)
    def test_backward_clock(self):
        c=Controller();c.arm();c.update(1000,100);self.assertFalse(c.update(9000,99)[0]);self.assertFalse(c.armed)
    def test_continuous_requires_opt_in(self):
        with self.assertRaises(ValueError):Controller(cap_ms=0)
        c=Controller(cap_ms=0,allow_continuous=True);c.arm();c.update(1000,0)
        self.assertTrue(c.update(9000,1)[0]);self.assertTrue(c.update(9000,20000)[0]);self.assertFalse(c.update(1000,20001)[0])
    def test_pinmap_and_default(self):
        self.assertEqual((C.DIR_L,C.PWM_L,C.DIR_R,C.PWM_R),(1,0,10,2))
        self.assertEqual((C.MIC_PIN,C.ARM_PIN),(3,6));self.assertFalse(C.HARDWARE_CHECKED)
        self.assertEqual(C.PROFILE,'commissioning');self.assertLessEqual(C.PWM_DUTY,.5)

if __name__=='__main__':unittest.main()
