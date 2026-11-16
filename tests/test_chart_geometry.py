import unittest
from src.day07.chart_geometry import fit_axis


class AxisTests(unittest.TestCase):
    def test_linear_tick_calibration(self):
        axis=fit_axis([(10,400),(30,300),(50,200),(70,100)])
        self.assertAlmostEqual(axis['baseline_y'],90)
        self.assertAlmostEqual(axis['slope']*49+axis['intercept'],205)

    def test_nonlinear_or_inverted_axis_is_not_treated_as_linear_bar_chart(self):
        self.assertIsNone(fit_axis([(10,100),(30,10),(50,1)]))
        self.assertIsNone(fit_axis([(10,0),(30,100),(50,200)]))

    def test_insufficient_or_repeated_ticks_cannot_establish_a_scale(self):
        self.assertIsNone(fit_axis([(10,400),(50,200)]))
        self.assertIsNone(fit_axis([(10,100),(10,200),(10,300)]))


if __name__=='__main__':unittest.main()
