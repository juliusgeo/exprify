irr, n, ra = 283, 256, range(256)


def m(x, y):
    r = 0
    while y:
        (y & 1) and (r := r ^ x)
        y >>= 1
        x <<= 1
        (x & n) and (x := x ^ irr)
    return r


def exp(a, p):
    pr = 1
    while p != 0:
        (p & 1) and (pr := m(pr, a))
        p >>= 1
        a = m(a, a)
    return pr


def bf(a, m=0):
    return ((a << m) | (a >> (8 - m))) & 255


def f(a, c):
    ret = 0
    for i in c:
        ret ^= bf(a, i)
    return ret ^ 0x5 if c[0] else ret ^ 0x63


def v(a):
    return exp(a, n - 2)


sb = [f(v(i), range(5)) for i in ra]
isb = [v(f(i, [1, 3, 6])) for i in ra]


def pprint_box(box):
    box = ["%.2x " * 16 % (*box[r : r + 16],) for r in range(n)[::16]]
    for line in box:
        print(line)


pprint_box(sb)
pprint_box(isb)
