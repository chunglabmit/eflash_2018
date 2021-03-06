import argparse
import json
import numpy as np
import pickle
import h5py
import sys

def parse_args(args=sys.argv[:1]):
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-file",
                        required=True,
                        help="Patch file generated by collect-patches")
    parser.add_argument("--model",
                        required=True,
                        help="Model file from eflash-train")
    parser.add_argument("--output",
                        required=True,
                        help="Output file of filtered blob coordinates")
    parser.add_argument("--threshold",
                        default=.5,
                        type=float,
                        help="Cutoff threshold for classifier")
    return parser.parse_args(args)

def main(args=sys.argv[1:]):
    opts = parse_args(args)
    patch_file = h5py.File(opts.patch_file, "r")
    with open(opts.model, "rb") as fd:
        model = pickle.load(fd)
    blobs = np.column_stack([patch_file[_][:] for _ in "zyx"])
    patches = []
    for p in (patch_file["patches_xy"], patch_file["patches_xz"], patch_file["patches_yz"]):
        patches.append(p[:].reshape(len(p), -1))
    patches = np.hstack(patches)

    pca = model["pca"]
    pca_patches = pca.transform(patches)
    classifier = model["classifier"]
    if classifier.n_features_ == pca_patches.shape[1] + 3:
        # User had --use-position. We do the best we can...
        pca_patches = np.column_stack((pca_patches, blobs[:, 2], blobs[:, 1], blobs[:, 0]))
    probs = classifier.predict_proba(pca_patches)[:, 1]
    positive = blobs[probs > opts.threshold]
    with open(opts.output, "w") as fd:
        json.dump(positive[:, ::-1].tolist(), fd)


if __name__ == "__main__":
    main()
