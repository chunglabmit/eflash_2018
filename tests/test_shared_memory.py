import multiprocessing
import numpy as np
import unittest
from eflash_2018.utils.shared_memory import SharedMemory


def write_something(shm:SharedMemory, idx, value):
    with shm.txn() as m:
        m[idx] = value


def read_something(shm:SharedMemory, idx):
    with shm.txn() as m:
        return m[idx]


class TestSharedMemory(unittest.TestCase):
    def test_subprocess_write(self):
        shm = SharedMemory((100, 100), np.uint16)
        with shm.txn() as m:
            m[:] = 0
        with multiprocessing.Pool(1) as pool:
            pool.apply(write_something, (shm, (40, 50), 89))
        with shm.txn() as m:
            self.assertEqual(m[40, 50], 89)

    def test_subprocess_read(self):
        shm = SharedMemory((100, 100), np.uint16)
        a = np.random.RandomState(1234).randint(0, 65535, (100, 100))
        with shm.txn() as m:
            m[:] = a
        with multiprocessing.Pool(1) as pool:
            result = pool.apply(read_something, (shm, (55, 33)))
        self.assertEqual(a[55, 33], result)

if __name__ == '__main__':
    unittest.main()
