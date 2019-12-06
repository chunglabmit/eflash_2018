import contextlib
import os
import numpy as np
import sys
import tempfile

if sys.version >= "3.8":
    has_multiprocessing_shared_memory = True
    import multiprocessing.shared_memory
else:
    has_multiprocessing_shared_memory = False

if sys.platform.startswith("linux"):
    is_linux = True
elif not has_multiprocessing_shared_memory:
    raise NotImplementedError(
        "SharedMemory is only supported on Linux or Python 3.8+")


class SharedMemory:
    """A class to share memory between processes

    Instantiate this class in the parent process and use in all processes.

    For all but Linux, we use the mmap module to get a buffer for Numpy
    to access through numpy.frombuffer. But in Linux, we use /dev/shm which
    has no file backing it and does not need to deal with maintaining a
    consistent view of itself on a disk.

    Typical use:

    shm = SharedMemory((100, 100, 100), np.float32)

    def do_something():

        with shm.txn() as a:

            a[...] = ...

    with multiprocessing.Pool() as pool:

        pool.apply_async(do_something, args)

    """
    if not has_multiprocessing_shared_memory:

        def __init__(self, shape, dtype):
            """Initializer

            :param shape: the shape of the array

            :param dtype: the data type of the array
            """
            directory = "/dev/shm"
            self.tempfile = tempfile.NamedTemporaryFile(
                prefix="proc_%d_" % os.getpid(),
                suffix=".shm",
                dir=directory,
                delete=True)
            self.pathname = self.tempfile.name
            self.shape = shape
            self.dtype = np.dtype(dtype)

        @contextlib.contextmanager
        def txn(self):
            """ A contextual wrapper of the shared memory

            :return: a view of the shared memory which has the shape and
            dtype given at construction
            """
            with open(self.pathname, mode="r+b") as fd:
                memory = np.memmap(fd,
                                   shape=self.shape,
                                   dtype=self.dtype)
            yield memory
            del memory

        def __getstate__(self):
            return self.pathname, self.shape, self.dtype

        def __setstate__(self, args):
            self.pathname, self.shape, self.dtype = args
    else:
        def __init__(self, shape, dtype):
            """Initializer

            :param shape: the shape of the array

            :param dtype: the data type of the array
            """
            self.shape = shape
            self.dtype = np.dtype(dtype)
            self.shm = multiprocessing.shared_memory.SharedMemory(
                create=True,
                size=int(np.prod(shape) * self.dtype.itemsize))
            self.name = self.shm.name

        def __getstate__(self):
            return self.name, self.shape, self.dtype

        def __setstate__(self, args):
            self.name, self.shape, self.dtype = args
            self.shm = multiprocessing.shared_memory.SharedMemory(
                name=self.name,
                create=False,
                size=np.prod(self.shape) * np.prod(self.dtype.itemsize))
            self.i_am_a_clone = True

        @contextlib.contextmanager
        def txn(self):
            """ A contextual wrapper of the shared memory

            :return: a view of the shared memory which has the shape and
            dtype given at construction
            """
            a = np.ndarray(self.shape, self.dtype, buffer=self.shm.buf)
            yield a

        def __del__(self):
            self.shm.close()
            if not hasattr(self, "i_am_a_clone"):
                self.shm.unlink()

