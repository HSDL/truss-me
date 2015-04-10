import numpy
from trussme import truss
import unittest


class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.T = truss.Truss()

    def test_truss(self):

        self.T.add_support(numpy.array([0.0, 0.0, 0.0]), d=2)
        self.T.add_joint(  numpy.array([1.0, 0.0, 0.0]), d=2)
        self.T.add_joint(  numpy.array([2.0, 0.0, 0.0]), d=2)
        self.T.add_joint(  numpy.array([3.0, 0.0, 0.0]), d=2)
        self.T.add_joint(  numpy.array([4.0, 0.0, 0.0]), d=2)
        self.T.add_support(numpy.array([5.0, 0.0, 0.0]), d=2)

        self.T.add_joint(  numpy.array([0.5, 1.0, 0.0]), d=2)
        self.T.add_joint(  numpy.array([1.5, 1.0, 0.0]), d=2)
        self.T.add_joint(  numpy.array([2.5, 1.0, 0.0]), d=2)
        self.T.add_joint(  numpy.array([3.5, 1.0, 0.0]), d=2)
        self.T.add_joint(  numpy.array([4.5, 1.0, 0.0]), d=2)

        self.T.joints[7].loads[1] = -20000
        self.T.joints[8].loads[1] = -20000
        self.T.joints[9].loads[1] = -20000

        self.T.add_member(0, 1)
        self.T.add_member(1, 2)
        self.T.add_member(2, 3)
        self.T.add_member(3, 4)
        self.T.add_member(4, 5)

        self.T.add_member(6, 7)
        self.T.add_member(7, 8)
        self.T.add_member(8, 9)
        self.T.add_member(9, 10)

        self.T.add_member(0, 6)
        self.T.add_member(6, 1)
        self.T.add_member(1, 7)
        self.T.add_member(7, 2)
        self.T.add_member(2, 8)
        self.T.add_member(8, 3)
        self.T.add_member(3, 9)
        self.T.add_member(9, 4)
        self.T.add_member(4, 10)
        self.T.add_member(10, 5)

        self.T.set_goal(min_fos_buckling=1.5,
                        min_fos_yielding=1.5,
                        max_mass=5.0,
                        max_deflection=6e-3)

        self.T.print_report()

if __name__ == "__main__":
    unittest.main()
