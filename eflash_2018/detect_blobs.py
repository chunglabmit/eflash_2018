import multiprocessing
import argparse
import itertools
import json
import numpy as np
import scipy.ndimage as ndi
import glob
from eflash_2018.utils.shared_memory import SharedMemory
import tifffile
import tqdm

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",
                        required=True,
                        help="Source image stack")
    parser.add_argument("--output",
                        required=True,
                        help="JSON file containing coordinates")
    parser.add_argument("--dog-low",
                        type=float,
                        default=4.0,
                        help="Sigma of the first Gaussian in the difference")
    parser.add_argument("--dog-high",
                        type=float,
                        default=10.0,
                        help="Sigma of the second Gaussian in the difference")
    parser.add_argument("--threshold",
                        type=float,
                        default=25.0,
                        help="Threshold cutoff for blobs")
    parser.add_argument("--min-distance",
                        type=float,
                        default=3,
                        help="Minimum distance between blobs")
    parser.add_argument("--invert",
                        action="store_true",
                        help="Invert the intensity of the difference of "
                        "Gaussians in order to find dark centers (e.g. in "
                        "the nuclei of a cytoplasmic stain)")
    parser.add_argument("--block-size-xy",
                        type=int,
                        default=1024,
                        help="Size of a processing block in the x and y "
                             "direction")
    parser.add_argument("--block-size-z",
                        type=int,
                        default=100,
                        help="Size of a processing block in the z direction")
    parser.add_argument("--padding-xy",
                        type=int,
                        default=20,
                        help="Overlap between blocks in the x and y direction")
    parser.add_argument("--padding-z",
                        type=int,
                        default=5,
                        help="Padding in the Z direction")
    return parser.parse_args()


def read_plane(stackmem, filename, offset):
    with stackmem.txn() as m:
        m[offset] = tifffile.imread(filename)


def do_dog(imgmem, dog_low, dog_high,
           x0, x1, y0, y1, z0, z1, x0p, x1p, y0p, y1p, z0p, z1p,
           min_distance, threshold, invert):
    imd = int(np.ceil(min_distance))
    structure = np.sum(
        np.square(np.mgrid[-imd:imd+1, -imd:imd+1, -imd:imd+1]), 0) <= \
        np.square(min_distance)
    with imgmem.txn() as img:
        mini_img = img[:, y0p:y1p, x0p:x1p].astype(np.float32)
        dog = ndi.gaussian_filter(mini_img, dog_low) - \
               ndi.gaussian_filter(mini_img, dog_high)
        if invert:
            dog = -dog
        zc, yc, xc = np.where(dog == ndi.grey_dilation(
            dog, footprint=structure))
        zca = zc + z0p
        yca = yc + y0p
        xca = xc + x0p
        mask = (dog[zc, yc, xc] > threshold) & (zca >= z0) & (zca < z1) &\
               (yca >= y0) & (yca < y1) & (xca >= x0) & (xca < x1)
        return np.column_stack((xca[mask], yca[mask], zca[mask]))


def main():
    args = parse_arguments()
    files = sorted(glob.glob(args.source))
    first_plane = tifffile.imread(files[0])
    x_extent = first_plane.shape[1]
    y_extent = first_plane.shape[0]
    z_extent = len(files)
    x0a = np.arange(args.padding_xy, x_extent, args.block_size_xy)
    x1a = x0a + args.block_size_xy
    x1a[-1] = x_extent - args.padding_xy
    x0p = x0a - args.padding_xy
    x1p = x1a + args.padding_xy
    x1p[-1] = x_extent
    y0a = np.arange(args.padding_xy, y_extent, args.block_size_xy)
    y1a = y0a + args.block_size_xy
    y1a[-1] = y_extent - args.padding_xy
    y0p = y0a - args.padding_xy
    y1p = y1a + args.padding_xy
    y1p[-1] = y_extent
    points = []
    for z0 in range(args.padding_z, z_extent - args.padding_z, args.block_size_z):
        z1 = min(z0 + args.block_size_z, z_extent - args.padding_z)
        z0p = z0 - args.padding_z
        z1p = min(z1 + args.padding_z, z_extent)
        img_mem = SharedMemory((z1p-z0p, y_extent, x_extent), first_plane.dtype)
        with multiprocessing.Pool(12) as pool:
            futures = []
            for z in range(z0p, z1p):
                futures.append(pool.apply_async(read_plane,
                                           (img_mem, files[z], z - z0p)))
            for future in tqdm.tqdm(futures, desc="Reading stack"):
                future.get()
        with multiprocessing.Pool() as pool:
            futures = []
            for xi, yi in itertools.product(range(len(x0a)), range(len(y0a))):
                futures.append(pool.apply_async(
                    do_dog,
                    (img_mem, args.dog_low, args.dog_high,
                     x0a[xi], x1a[xi], y0a[yi], y1a[yi], z0, z1,
                     x0p[xi], x1p[xi], y0p[yi], y1p[yi], z0p, z1p,
                     args.min_distance, args.threshold, args.invert)
                ))
            for future in tqdm.tqdm(futures, desc="Computing"):
                points.append(future.get())
    points = np.vstack(points)
    with open(args.output, "w") as fd:
        json.dump(points.tolist(), fd)


if __name__ == "__main__":
    main()
