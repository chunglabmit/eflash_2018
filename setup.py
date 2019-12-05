from setuptools import setup

version = "0.1.0"

setup(
    name="eflash-2018",
    version=version,
    description="Software used in the EFlash paper",
    install_requires=[
        "h5py",
        "matplotlib",
        "scipy",
        "scikit-learn",
        "scikit-image",
        "tifffile",
        "tqdm"
    ],
    author="Kwanghun Chung Lab",
    packages=["eflash_2018",
              "eflash_2018.utils"],
    entry_points=dict(console_scripts=[
        "detect-blobs=eflash_2018.detect_blobs:main",
        "collect-patches=eflash_2018.collect_patches:main",
        "eflash-train=eflash_2018.train:main",
        "eflash-display=eflash_2018.ngdisplay_ui:main"
    ])
)