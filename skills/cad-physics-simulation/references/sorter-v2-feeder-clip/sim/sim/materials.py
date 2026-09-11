"""Part name -> material.

The rules are the ones the render pipeline settled on for the machine's
approved look, ported so the simulation, the viewer and any offline render
agree on what each part is made of. `classify(name, path)` returns a material
key; MATERIALS maps a key to its look. Parts that return None keep the colour
the CAD export carries (electronics, servos, wiring, labels).
"""
from __future__ import annotations

import re

# rgba plus MuJoCo material terms (specular 0-1, shininess 0-1, reflectance 0-1, emission 0+).
MATERIALS: dict[str, dict] = {
    "pla_black": dict(rgba=(0.012, 0.012, 0.012, 1), specular=0.45, shininess=0.28),
    "pla_white": dict(rgba=(0.86, 0.86, 0.85, 1), specular=0.45, shininess=0.32),
    "pla_gray": dict(rgba=(0.20, 0.20, 0.20, 1), specular=0.45, shininess=0.30),
    "pla_light_gray": dict(rgba=(0.70, 0.70, 0.70, 1), specular=0.45, shininess=0.30),
    "alu_black": dict(rgba=(0.02, 0.02, 0.022, 1), specular=0.6, shininess=0.58, reflectance=0.2),
    "chrome": dict(rgba=(0.82, 0.82, 0.82, 1), specular=1.0, shininess=0.72, reflectance=0.4),
    "cardboard": dict(rgba=(0.53, 0.325, 0.150, 1), specular=0.2, shininess=0.1),
    "plywood": dict(rgba=(0.74, 0.56, 0.34, 1), specular=0.4, shininess=0.5),
    "reflector": dict(rgba=(0.92, 0.92, 0.92, 1), specular=0.4, shininess=0.45, emission=0.6),
}

FASTENER = re.compile(
    r"(screw|washer|\bnut\b|hex nut|flange nut|slot nut|insert|ruthex|rivet|parallel pin|"
    r"t-slot|set screw|boss)", re.I)
BIN = re.compile(r"^bin_(half|third)_", re.I)
FUNNEL = re.compile(r"funnel", re.I)
PROFILE = re.compile(r"(2020 guide profile|vertical_beam|top_beam)", re.I)
KEEP = re.compile(
    r"(caster|servo|mg995|wires-1|wire boot|"
    r"06247695|pcb|conductor ribbon|ribbon wire|idc|jst|pin ?header|socket$|capacitor|"
    r"orange pi 5 |usb|hdmi|rj45|tmc2209|pico|rp2040|heatsink|label|led|selector|"
    r"terminal block|voltage trim|mean well|psu internal|psu cooling fan|psu fan hub|"
    r"acridine|waveshare|converter|receptacle|stub|mock-|_0603_|c1_actual|"
    r"conn_|pca9|25mhz|tactile|bootsel|adapter-populated|envelope|foot connector|"
    r"2020 m6)", re.I)
CHUTE_WHITE = re.compile(
    r"(gen4_core|gen3_bearing|gen3_flap|gen3_servo_(cover|side_connector|housing)|"
    r"gen3_side_arm|gen3_lower_arm|gen3_chute_flap|gen3 connector|gen3 top connector|"
    r"gen3_left_bearing)", re.I)
ELEC_BOX = re.compile(
    r"^(base|wall-(west|east|north|south)|roof|duct|antenna-clamp-(backer|base|cap)|hub-clamp|"
    r"buck-clamp|plunger(-retainer|-cap)?|cover|retainer|shell front module|shell rear tray|"
    r"front panel|lid front|lid rear)$", re.I)
LED_HOOK = re.compile(r"inner reflector led hook", re.I)
ELEC_ASSEMBLY = re.compile(r"(Orange Pi assembly|Basically board assembly|PSU assembly)")


def classify(name: str, path: list[str]) -> str | None:
    """Material key for a part, or None to keep the export's own colour.

    `path` is the chain of sub-assembly names above the part, root first.
    """
    n = name
    anc = " / ".join(path)
    if BIN.search(n):
        return "cardboard"
    if n == "lamp inner reflector":
        return "reflector"
    if LED_HOOK.search(n):
        return "pla_white"
    if n.startswith("Top plate"):
        return "plywood"
    if n == "cage_bracket_ribbon":
        return "pla_black"
    if re.search(r"(dummy camera|nema17|nema23|stepper|mg995|mock-)", n, re.I):
        return "pla_black"
    if re.search(r"(lazy_susan|lazy suzan|shaft-1)", n, re.I):
        return "chrome"
    if n == "Servomotor arm":
        return "pla_white"
    if FASTENER.search(n):
        return "chrome"
    if FUNNEL.search(n):
        return "pla_gray"
    if PROFILE.search(n):
        return "alu_black"
    if "0002_Chute" in anc and CHUTE_WHITE.search(n):
        return "pla_white"
    if ELEC_ASSEMBLY.search(anc) and ELEC_BOX.search(n):
        return "pla_black"
    if KEEP.search(n):
        return None
    if "0002_Chute" in anc:
        return None
    if "full feeder assembly" in anc:
        # Rotors and stators are the light grey of the lamp shade in the CAD;
        # the rest of the feeder is printed in the same dark grey as the frame.
        if n.startswith(("Rotor", "Stator", "rotor cap", "Output Guide")):
            return "pla_light_gray"
        return "pla_gray"
    if ELEC_ASSEMBLY.search(anc):
        return None
    return "pla_black"
