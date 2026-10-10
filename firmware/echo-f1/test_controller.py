import unittest,math
from controller import Controller,level

class LogicTests(unittest.TestCase):
    def test_initial_stop(self):
        self.assertFalse(Controller().update(5000,0)[0])
    def test_arm_requires_quiet(self):
        c=Controller();c.arm();self.assertFalse(c.update(5000,0)[0])
        c.update(20,40);self.assertTrue(c.update(1500,80)[0])
    def test_quiet_stops(self):
        c=Controller();c.arm();c.update(0,0);c.update(2000,40)
        self.assertFalse(c.update(700,80)[0])
    def test_hysteresis(self):
        c=Controller();c.arm();c.update(0,0)
        self.assertFalse(c.update(850,40)[0]);self.assertTrue(c.update(1100,80)[0]);self.assertTrue(c.update(850,120)[0])
    def test_run_cap(self):
        c=Controller();c.arm();c.update(0,0);c.update(2000,40)
        self.assertFalse(c.update(2000,5040)[0]);self.assertFalse(c.update(2000,6000)[0])
        c.update(0,7000);self.assertTrue(c.update(2000,8000)[0])
    def test_fault_disarms(self):
        for value in [None,float('nan'),float('inf'),-1]:
            c=Controller();c.arm();c.update(0,0);self.assertFalse(c.update(value,10)[0]);self.assertFalse(c.armed)
    def test_stale_stops(self):
        c=Controller();c.arm();c.update(0,0);self.assertFalse(c.update(2000,300,300)[0])
    def test_stop_button(self):
        c=Controller();c.arm();c.update(0,0);c.update(2000,40);c.stop();self.assertFalse(c.update(2000,80)[0])
    def test_level_dc_removed(self):
        self.assertEqual(level([32768]*160),0)
        self.assertAlmostEqual(level([31768,33768]*80),1000)
    def test_level_rails(self):
        for samples in [[0]*160,[65535]*160,[0,65535]*80,[float('nan')]*160,[]]:self.assertIsNone(level(samples))
    def test_no_start_at_equality(self):
        c=Controller();c.arm();c.update(0,0);self.assertFalse(c.update(1000,40)[0])
    def test_invalid_configuration(self):
        for args in [(600,700,5000),(1000,700,0),(1000,700,99999)]:
            with self.assertRaises(ValueError):Controller(*args)
    def test_explicit_continuous_profile(self):
        c=Controller(cap_ms=0,allow_continuous=True);c.arm();c.update(0,0)
        self.assertTrue(c.update(2000,10)[0]);self.assertTrue(c.update(2000,99999)[0])
        self.assertFalse(c.update(100,100100)[0])

if __name__=='__main__': unittest.main(verbosity=2)
