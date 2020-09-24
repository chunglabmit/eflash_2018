# EFlash 2018

[![Travis CI Status](https://travis-ci.org/chunglabmit/eflash-2018.svg?branch=master)](https://travis-ci.org/chunglabmit/eflash-2018)

This repository holds software used to analyze data for the Chung Lab's
EFlash paper.

The analysis pipeline has three steps:

* Find putative positive cells using **detect-blobs**
* Make a list of patches for training using **collect-patches**
* Train a model and predict positives using **eflash-train**

## detect-blobs

**detect-blobs** is a simple blob detector. It looks for peaks in the
local maximum using a difference of gaussians followed by a simple
static thresholding of points found to have higher signal than their
neighbors.

Usage:
```
detect-blobs \
    --source <source-expr> \
    --output <coords-file> \
    [--dog-low <dog-low-sigma>] \
    [--dog-low-xy <dog-low-sigma-xy>] \
    [--dog-low-z <dog-low-sigma-z>] \
    [--dog-high <dog-high-sigma>] \
    [--dog-high-xy <dog-high-sigma-xy>] \
    [--dog-high-z <dog-high-sigma-z>] \
    [--threshold <threshold>] \
    [--min-distance <min-distance>] \
    [--min-distance-xy <min-distance-xy>] \
    [--min-distance-z <min-distance-z>] \
    [--block-size-xy <block-size-xy>] \
    [--block-size-z <block-size-z>] \
    [--padding-xy <padding-xy>] \
    [--padding-z <padding-z>]

```
Where
* *source-expr* is a GLOB expression for collecting the .tiff files that make
up the stack. For instance "/home/alice/myfiles/*.tiff".
* *output* is the name of the output file. This will be a json-encoded list of
lists where the inner list has the X, Y and Z coordinates of a putatitive cell
in that order.
* *dog-low-sigma* is the standard deviation of the Gaussian used to smooth the
foreground of the image.
* *dog-low-sigma-xy* and *dog-low-sigma-z* are the foreground standard
deviations in the X/Y and Z directions if the volume is anisotropic
* *dog-high-sigma* is the standard deviation of the Gaussian used to smooth the
background of the image. The smoothed background is subtracted from the smoothed
foreground to get the difference of Gaussians (dog).
* *dog-high-sigma-xy* and *dog-high-sigma-z* are the background standard
deviations in the X/Y and Z directions if the volume is anisotropic
* *threshold* is the absolute cutoff for peak finding. Any peak must have a
value above this threshold in the difference of Gaussians.
* *min-distance* is the minimum distance in voxels between adjacent peaks. The
peak with the higher intensity is chosen if two are within this distance. Large
minimum distances can be computationally expensive.
* *min-distance-xy* and *min-distance-z* are the minimum distances
in the X/Y and Z directions if the volume is anisotropic
* *block-size-xy* is the size of a processing block in the X and Y direction.
The block size (block-size-xy * block-size-xy * block-size-z) times the number
of cores times 8 should be less than your memory size.
* *block-size-z* is the size of a processing block in the Z direction
* *padding-xy* is the amount of padding on the x and y sides of a block. It
should be large enough for the larger Gaussian to be properly computed.
* *padding-z* is the amount of padding in the Z direction above and below a
block.

## collect-patches

**collect-patches** assembles rectangular 2D patches around the vicinity of
detected putatitive centers as detected by **detect-blobs**.

Usage:
```text
collect-patches \
    --source <source-expr> \
    --points <points> \
    --output <output> \
    [--patch-size <patch-size>] \
    [--n-cores <n-cores>]
```

Where
* **source-expr** is a glob expression to collect the .tiff files in the stack
(see **detect-blobs**)
* **points** is the file output by **detect-blobs**
* **output** is the HDF5 file containing the patches and their coordinates.
The file has four datasets, 
  * *patches* - an N * M * M sized array where N is the
number of points and M is the patch size.
  * *x* the X coordinates of each of the N points
  * *y* the Y coordinates of each of the N points
  * *z* the Z coordinates of each of the N points
* **patch-size** - the size of the patch centered on each point. This should
be an odd number so that the same number of pixels are to the left and right
of the center point.
* **n-cores** - the number of simultaneous parallel processes to spawn. This
should be fewer than the number of CPUs on your machine and might be 
substantially fewer if the machine has a low I/O bandwidth to the data source.

## eflash-train

**eflash-train** is an interactive program that lets the user train a classifier
based on the patches output by **collect-patches**

### Technical details

**eflash-train** first applies dimensionality reduction to the raw patch data.
It creates a flat array per patch and then finds the first 24 principal
components of the patch data. This creates a feature bank of 24 features.

The features are then used, along with the user's classification of a small
number of examples, to train a random forest classifier. This classifier is then
used to predict whether each putative cell is a true cell or false positive.

Usage:
```text
eflash-train \
    --patch-file <patch-file> \
    --output <output> \
    [--neuroglancer <image-source>] \
    [--port <port>] \
    [--bind-address <bind-address>] \
    [--static-content-source <static-content-source>]
```

where
* **patch-file** is the name of the file produced by **collect-patches**
* **output** is the name of the model file to be generated
* **neuroglancer** is the name of a Neuroglancer data source, for instance,
  "precomputed://http://localhost:81". This is optional, but if present,
  **eflash-train** will present a Neuroglancer view and will reposition the
   view at the current cell every time a new cell is selected.
* **port** is the port number on which to launch the Neuroglancer view.
  By default, any available port is selected.
* **bind-address** is the IP address to bind Neuroglancer's listening
  port to. By default, this is the loopback address, "localhost".
* **static-content-source** is the static content source server URL for
  Neuroglancer's assets. By default, this is the Neuroglancer demo server.
  See 
  [the neuroglancer documentation](https://github.com/google/neuroglancer/blob/master/python/README.md)
  for details on the demo server. 

The GUI has the following menu commands:
* File
  * **Save** (ctrl + S) saves the output model file. This also saves the
              positive and negative ground-truth so that you can restart the
              session where you left off.
  * **Write** writes the coordinates classified as positive to a points .json
              file.
  * **Train** (T) trains the model.
  * **Quit** shuts the program down
* Image
  * **Next** (X) displays a random unclassified patch for user classification
  * **Next Positive** (ctrl+P) displays a random unclassified patch that the
             model believes is positive.
  * **Next Negative** (ctrl+N) displays a random unclassified patch that the
             model believes is negative.
  * **Next Unsure** (U) displays a random unclassified patch that the model
             predicts as positive or negative with roughly equal probability.
* Mark
  * **Positive** Mark the currently displayed patch as a positive example
  * **Negative** Mark the currently displayed patch as a negative example

In a typical training session, a user first classifies 10-20 cells using
Image->Next followed by Mark->Positive or Mark->Negative as appropriate. After
that, the user trains a model using File->Train and then classifies 10-20
unsure patches (using Image->Next Unsure and Mark->Positive and Negative).
The user then retrains and classifies another 10-20 unsure patches.
Periodically, the user can scan some representative patches classified as
positive or negative using Image->Next Positive or Negative, verifying the
accuracy by eye. Generally, too few images will be classified to calculate
reasonable statistics for the model's accuracy, e.g. through out-of-bag error.

## eflash-predict

**eflash-predict** applies the model from **eflash-train** to a patch file from
another dataset.

Usage:

```text
eflash-predict \
  --model <model-file> \
  --patch-file <patch-file> \
  --output <output> \
  [--threshold <threshold>]
```

where

* **model-file** is the model file created by eflash-train

* **patch-file** is the patch file generated by **collect-patches**

* **output** is the name of the output file, a json file of coordinates that 
  the classifier classifies as positives.

* **threshold** is a number between 0 and 1 which is the probability cutoff threshold
  for positives (higher = more restrictive)

###Credits
training.png made by Freepik from www.flaticon.com  