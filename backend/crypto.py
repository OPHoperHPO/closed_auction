import random

from fastecdsa.curve import Curve
from fastecdsa.point import Point


class PyPedersen:
    def __init__(self,
                 q=21888242871839275222246405745257275088696311157297823662689037894645226208583,
                 gX=19823850254741169819033785099293761935467223354323761392354670518001715552183,
                 gY=15097907474011103550430959168661954736283086276546887690628027914974507414020,
                 hX=3184834430741071145030522771540763108892281233703148152311693391954704539228,
                 hY=1405615944858121891163559530323310827496899969303520166098610312148921359100):
        self.curve = Curve(
            "bn128",  # (str): The name of the curve
            q,
            # (long): The value of p in the curve equation.
            0,  # (long): The value of a in the curve equation.
            3,  # (long): The value of b in the curve equation.
            q,
            # (long): The order of the base point of the curve.
            gX,
            # (long): The x coordinate of the base point of the curve.
            gY,
            # (long): The y coordinate of the base point of the curve.
        )
        self.G = Point(gX, gY, curve=self.curve)
        self.H = Point(hX, hY, curve=self.curve)
        self.B = 10 ** 19  # Макс ставка 10 eth

    def commit(self, x: int, r: int):
        """
        C = x*G + r*H
        :param x: ставка в WEI
        :param r: любое число
        :return Cx, Cy
        """
        C = (x * self.G) + (r * self.H)
        return C.x, C.y
    
    def commit_neg(self, x: int, r: int):
        """
        C = -x*G + r*H
        :param x: ставка в WEI
        :param r: любое число
        :return Cx, Cy
        """
        G_temp = self.G
        C = (x * G_temp) + (r * self.H)
        return C.x, C.y

    def verify(self, x, r, cX, cY) -> bool:
        cX2, cY2 = self.commit(x, r)
        return cX == cX2 and cY == cY2

    def commit_delta(self, cX, cY, cX2, cY2):
        c = Point(cX, cY, curve=self.curve)
        c2 = Point(cX2, cY2, curve=self.curve)
        out = c + c2
        return out.x, out.y

    def get_w1_w2(self):
        w1 = random.randint(0, self.B / 2)
        w2 = abs(w1 - self.B)
        r1 = random.randint(0, self.B / 2)
        r2 = random.randint(0, self.B / 2)
        W1 = self.commit(w1, r1)
        W2 = self.commit_neg(w2, r2)
        return W1[0], W1[1], W2[0], W2[1], w1, r1, w2, r2
