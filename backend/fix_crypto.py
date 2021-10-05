from fastecdsa.curve import Curve 
from fastecdsa.point import Point

bn128 = Curve(
    "bn128",  # (str): The name of the curve
    21888242871839275222246405745257275088696311157297823662689037894645226208583,  # (long): The value of p in the curve equation.
    0,  # (long): The value of a in the curve equation.
    3,  # (long): The value of b in the curve equation.
    21888242871839275222246405745257275088548364400416034343698204186575808495617,  # (long): The order of the base point of the curve.
    19823850254741169819033785099293761935467223354323761392354670518001715552183,  # (long): The x coordinate of the base point of the curve.
    15097907474011103550430959168661954736283086276546887690628027914974507414020,  # (long): The y coordinate of the base point of the curve.
    
)

gX = 19823850254741169819033785099293761935467223354323761392354670518001715552183
gY = 15097907474011103550430959168661954736283086276546887690628027914974507414020
hX = 3184834430741071145030522771540763108892281233703148152311693391954704539228
hY = 1405615944858121891163559530323310827496899969303520166098610312148921359100


G = Point(gX, gY, curve=bn128)
H = Point(hX, hY, curve=bn128)

def get_W2(b: int, r: int):
    point_new = G*(-1)
    point_temp = point_new*b + r*H
    return point_temp.x, point_temp.y