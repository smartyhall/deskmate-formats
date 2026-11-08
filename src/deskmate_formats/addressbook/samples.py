"""Fictional contacts for independent single-contact files, not a multirow book."""
from .personal import Contact


def contacts(count=25):
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError('expected 1..100 synthetic contacts')
    first = ('Alex', 'Morgan', 'Riley', 'Taylor', 'Sam')
    last = ('Example', 'Sample', 'Fiction', 'Test Person', 'Placeholder')
    cities = ('', 'Metro', 'Teston', 'Sample City', 'North Example')
    return tuple(Contact(first[n % 5], f'{last[(n // 5) % 5]} {n + 1:02d}',
                         cities[(n * 3) % 5], f'555-{100 + n:04d}') for n in range(count))
