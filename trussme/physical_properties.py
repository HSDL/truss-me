# Gravitational constant for computing weight from mass
g = 9.80665


# Material properties
materials = {"A36":     {"rho": 7800,
                         "E":   200*pow(10, 9),
                         "Fy":  250*pow(10, 6)},
             "A992":    {"rho": 7800,
                         "E":   200*pow(10, 9),
                         "Fy":  345*pow(10, 6)},
             "6061_T6": {"rho": 2700,
                         "E":   68.9*pow(10, 9),
                         "Fy":  276*pow(10, 6)}}


# Checks to see if material name is valid
def valid_member_name(name):
    if name in materials.keys():
        return True
    else:
        return False