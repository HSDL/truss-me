import numpy
from trussme import joint
from trussme import member
from trussme import report
from trussme.physical_properties import g
import time
import os


class Truss(object):

    def __init__(self):
        # Make a list to store members in
        self.members = []

        # Make a list to store joints in
        self.joints = []

        # Variables to store number of joints and members
        self.number_of_joints = 0
        self.number_of_members = 0

        # Variables to store truss characteristics
        self.mass = 0
        self.fos_yielding = 0
        self.fos_buckling = 0
        self.fos_total = 0
        self.limit_state = ''

        # Design goals
        self.goals = {"min_fos_total": -1,
                      "min_fos_buckling": -1,
                      "min_fos_yielding": -1,
                      "max_mass": -1,
                      "max_deflection": -1}
        self.THERE_ARE_GOALS = False

    def set_goal(self, **kwargs):
        self.THERE_ARE_GOALS = True
        for key in kwargs:
            if key is "min_fos_total":
                self.goals["min_fos_total"] = kwargs["min_fos_total"]
            elif key is "min_fos_yielding":
                self.goals["min_fos_yielding"] = kwargs["min_fos_yielding"]
            elif key is "min_fos_buckling":
                self.goals["min_fos_buckling"] = kwargs["min_fos_buckling"]
            elif key is "max_mass":
                self.goals["max_mass"] = kwargs["max_mass"]
            elif key is "max_deflection":
                self.goals["max_deflection"] = kwargs["max_deflection"]
            else:
                self.THERE_ARE_GOALS = False
                raise ValueError(key+' is not a valid defined design goal. '
                                     'Try min_fos_total, '
                                     'min_fos_yielding, '
                                     'min_fos_buckling, '
                                     'max_mass, or max_deflection.')

    def add_support(self, coordinates, d=3):
        # Make the joint
        self.joints.append(joint.Joint(coordinates))
        self.joints[self.number_of_joints].pinned(d=d)
        self.number_of_joints += 1

    def add_joint(self, coordinates, d=3):
        # Make the joint
        self.joints.append(joint.Joint(coordinates))
        self.joints[self.number_of_joints].free(d=d)
        self.number_of_joints += 1

    def add_member(self, joint_index_a, joint_index_b):
        # Make a member
        self.members.append(member.Member(self.joints[joint_index_a],
                                          self.joints[joint_index_b]))

        # Update joints
        self.joints[joint_index_a].members.append(self.members[-1])
        self.joints[joint_index_b].members.append(self.members[-1])

        self.number_of_members += 1

    def move_joint(self, joint_index, coordinates):
        self.joints[joint_index].coordinates = coordinates

    def calc_mass(self):
        self.mass = 0
        for m in self.members:
            self.mass += m.mass

    def set_load(self, joint_index, load):
        self.joints[joint_index].load = load

    def calc_fos(self):
        # Pull supports and add to D
        coordinates = []
        for j in self.joints:
            coordinates.append(j.coordinates)

        # Build Re
        reactions = numpy.zeros([3, self.number_of_joints])
        loads = numpy.zeros([3, self.number_of_joints])
        for i in range(len(self.joints)):
            reactions[0, i] = self.joints[i].translation[0]
            reactions[1, i] = self.joints[i].translation[1]
            reactions[2, i] = self.joints[i].translation[2]
            loads[0, i] = self.joints[i].loads[0]
            loads[1, i] = self.joints[i].loads[1]\
                - sum([m.mass/2.0*g for m in self.joints[i].members])
            loads[2, i] = self.joints[i].loads[2]

        # Pull out E and A
        elastic_modulus = []
        area = []
        connections = []
        for m in self.members:
            elastic_modulus.append(m.elastic_modulus)
            area.append(m.area)
            connections.append([j.idx for j in m.joints])

        # Make everything an array
        area = numpy.array(area)
        elastic_modulus = numpy.array(elastic_modulus)
        coordinates = numpy.array(coordinates).T
        connections = numpy.array(connections).T

        # Pull everything into a dict
        truss_info = {"elastic_modulus": elastic_modulus,
                      "coordinates": coordinates,
                      "connections": connections,
                      "reactions": reactions,
                      "loads": loads,
                      "area": area}

        forces, deflections, reactions = self.evaluate_forces(truss_info)

        for i in range(self.number_of_members):
            self.members[i].set_force(forces[i])

        for i in range(self.number_of_joints):
            for j in range(3):
                if self.joints[i].translation[j]:
                    self.joints[i].reactions[j] = reactions[j, i]
                    self.joints[i].deflections[j] = 0.0
                else:
                    self.joints[i].reactions[j] = 0.0
                    self.joints[i].deflections[j] = deflections[j, i]

        # Pull out the member factors of safety
        self.fos_buckling = min([m.fos_buckling if m.fos_buckling > 0
                                 else 10000 for m in self.members])
        self.fos_yielding = min([m.fos_yielding for m in self.members])

        # Get total FOS and limit state
        self.fos_total = min(self.fos_buckling, self.fos_yielding)
        if self.fos_buckling < self.fos_yielding:
            self.limit_state = 'buckling'
        else:
            self.limit_state = 'yielding'

    def evaluate_forces(self, truss_info):
        tj = numpy.zeros([3, numpy.size(truss_info["connections"], axis=1)])
        w = numpy.array([numpy.size(truss_info["reactions"], axis=0),
                         numpy.size(truss_info["reactions"], axis=1)])
        dof = numpy.zeros([3*w[1], 3*w[1]])
        deflections = numpy.ones(w)
        deflections -= truss_info["reactions"]

        # This identifies joints that can be loaded
        ff = numpy.where(deflections.T.flat == 1)[0]

        # Build the global stiffness matrix
        for i in range(numpy.size(truss_info["connections"], axis=1)):
            ends = truss_info["connections"][:, i]
            length_vector = truss_info["coordinates"][:, ends[1]] \
                - truss_info["coordinates"][:, ends[0]]
            length = numpy.linalg.norm(length_vector)
            direction = length_vector/length
            d2 = numpy.outer(direction, direction)
            ea_over_l = truss_info["elastic_modulus"][i]*truss_info["area"][i]/length
            ss = ea_over_l*numpy.concatenate((numpy.concatenate((d2, -d2), axis=1),
                                      numpy.concatenate((-d2, d2), axis=1)),
                                     axis=0)
            tj[:, i] = ea_over_l*direction
            e = list(range((3*ends[0]), (3*ends[0] + 3))) \
                + list(range((3*ends[1]), (3*ends[1] + 3)))
            for ii in range(6):
                for j in range(6):
                    dof[e[ii], e[j]] += ss[ii, j]

        SSff = numpy.zeros([len(ff), len(ff)])
        for i in range(len(ff)):
            for j in range(len(ff)):
                SSff[i, j] = dof[ff[i], ff[j]]

        Loadff = truss_info["loads"].T.flat[ff]
        Uff = numpy.linalg.solve(SSff, Loadff)

        ff = numpy.where(deflections.T == 1)
        for i in range(len(ff[0])):
            deflections[ff[1][i], ff[0][i]] = Uff[i]
        forces = numpy.sum(numpy.multiply(
            tj, deflections[:, truss_info["connections"][1, :]]
            - deflections[:, truss_info["connections"][0, :]]), axis=0)
        if numpy.linalg.cond(SSff) > pow(10, 10):
            forces *= pow(10, 10)
        reactions = numpy.sum(dof*deflections.T.flat[:], axis=1)\
            .reshape([w[1], w[0]]).T

        return forces, deflections, reactions

    def print_report(self):
        # DO the calcs
        self.calc_mass()
        self.calc_fos()

        print(time.strftime('%X %x %Z'))
        print(os.getcwd())

        report.print_summary(self)

        report.print_instantiation_information(self)

        report.print_stress_analysis(self)

        if self.THERE_ARE_GOALS:
            report.print_recommendations(self)
