"""Параметры двух ВРЕМЕННЫХ тестовых персонажей (не утверждённый дизайн).

amir     — мальчик 10 лет, базовое тело K10 (см. production/series/CHARACTERS.md)
babushka — бабушка 67 лет, базовое тело EL
"""

AMIR = dict(
    leg=0.46, torso=0.31, neck=0.035, head_r=0.165, sh_drop=0.035, sh_w=0.115, arm_angle=58,
    upper=0.165, fore=0.15, hand=0.07, finger=0.05, finger_gap=0.017, leg_w=0.068, thigh=0.215,
    ankle_h=0.065, foot=0.13, shoe_w=0.058, shoe_h=0.075,
    radii=dict(pelvis=0.104, spine=0.098, chest=0.106, clavroot=0.09, neck=0.045, shoulder=0.054, elbow=0.041,
               wrist=0.032, palm=0.035, finger=0.011, hip=0.072, knee=0.056, ankle=0.047, ball=0.045, toe=0.04),
    eye_sep=0.36, eye_up=0.10, eye_depth=0.79, eye_r=0.046, brow_up=0.31, brow_len=0.026, brow_th=0.0075, brow_tilt=4,
    nose_up=-0.13, nose_r=0.017, mouth_down=0.50, mouth_w=0.034, mouth_open=0.03, mouth_smile=0.004, jaw_drop=0.014,
    cheek=0.08, head_sx=1.02, head_sz=1.0, pole_angle=90, arm_pole_angle=-90, hoodie_hem=0.49, lid_open=60,
)

BABUSHKA = dict(
    leg=0.62, torso=0.43, neck=0.045, head_r=0.150, sh_drop=0.045, sh_w=0.145, arm_angle=62,
    upper=0.22, fore=0.195, hand=0.078, finger=0.054, finger_gap=0.018, leg_w=0.08, thigh=0.30,
    ankle_h=0.07, foot=0.145, shoe_w=0.06, shoe_h=0.07,
    radii=dict(pelvis=0.145, spine=0.14, chest=0.135, clavroot=0.115, neck=0.048, shoulder=0.056, elbow=0.044,
               wrist=0.034, palm=0.037, finger=0.0115, hip=0.078, knee=0.056, ankle=0.046, ball=0.05, toe=0.045),
    eye_sep=0.37, eye_up=0.09, eye_depth=0.81, eye_r=0.036, brow_up=0.32, brow_len=0.024, brow_th=0.0065, brow_tilt=-4,
    nose_up=-0.12, nose_r=0.021, mouth_down=0.50, mouth_w=0.031, mouth_open=0.024, mouth_smile=0.0045, jaw_drop=0.011,
    cheek=0.10, head_sx=1.04, head_sz=0.98, pole_angle=90, arm_pole_angle=-90, skirt_hem=0.17, skirt_r=0.27, lid_open=55,
)

HAND = ("index", "middle", "ring", "thumb", "hand")


def amir_zone(sp):
    def z(bone, c):
        if bone.startswith(HAND) or bone == "neck":
            return 3
        if bone.startswith(("foot", "toe")) or (bone.startswith("shin") and c.z < sp["ankle_h"] + 0.045):
            return 2
        if bone.startswith(("thigh", "shin")) or (bone == "pelvis" and c.z < sp["hoodie_hem"]):
            return 1
        return 0
    return z


def babushka_zone(sp):
    def z(bone, c):
        if bone.startswith(HAND) or bone == "neck":
            return 3
        if bone.startswith(("foot", "toe")) or (bone.startswith("shin") and c.z < sp["ankle_h"] + 0.04):
            return 2
        if bone.startswith(("thigh", "shin")) and c.z < sp["leg"] - 0.05:
            return 1
        return 0
    return z


AMIR_COLORS = dict(
    body=[("hoodie", (0.80, 0.22, 0.06), 0.85, 0.03), ("pants", (0.10, 0.17, 0.36), 0.8, 0.0),
          ("shoes", (0.85, 0.85, 0.82), 0.5, 0.0), ("skin", (0.80, 0.52, 0.36), 0.55, 0.0)],
    skin=(0.80, 0.52, 0.36), iris=(0.22, 0.11, 0.04), brow=(0.10, 0.06, 0.03), blush=(0.92, 0.38, 0.32),
    lip=(0.72, 0.36, 0.30), hair=(0.035, 0.02, 0.012), hood=(0.70, 0.18, 0.05),
    shoe=(0.85, 0.85, 0.82), sole=(0.75, 0.12, 0.08),
)

BABUSHKA_COLORS = dict(
    body=[("dress", (0.36, 0.14, 0.30), 0.85, 0.03), ("stockings", (0.42, 0.30, 0.22), 0.7, 0.0),
          ("shoes", (0.12, 0.07, 0.05), 0.4, 0.0), ("skin", (0.78, 0.55, 0.42), 0.6, 0.0)],
    skin=(0.78, 0.55, 0.42), iris=(0.20, 0.14, 0.08), brow=(0.55, 0.52, 0.50), blush=(0.88, 0.42, 0.38),
    lip=(0.66, 0.36, 0.32), scarf=(0.20, 0.42, 0.62), skirt=(0.30, 0.11, 0.25),
    shoe=(0.12, 0.07, 0.05), sole=(0.06, 0.04, 0.03),
)
