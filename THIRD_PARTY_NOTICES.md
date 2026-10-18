# Third-party components for image recognition

- **BioCLIP v1**, Imageomics Institute, MIT License.
  [Original model](https://huggingface.co/imageomics/bioclip) ·
  [Source and license](https://github.com/Imageomics/bioclip/blob/main/LICENSE).
  Browser-compatible fp16 image tower: [m3r1al/naturalist-bioclip-v1](https://huggingface.co/m3r1al/naturalist-bioclip-v1),
  pinned to revision `22a18d2fd141d2301968d93881b9e4431470c149`.
  SHA-256 `d982b6800a5b751272485ad4dd266f3d3eb39457b882daa5a0557cbbb62b3e9d`.
  Original image tower; no species-specific fine-tuning. The app supplies its own
  licensed photo references and does not use the export's plant/fungi text table.
  Full license: [licenses/BioCLIP-LICENSE.txt](licenses/BioCLIP-LICENSE.txt).

- **DINOv2 Small**, Meta Platforms, Inc. and affiliates, Apache License 2.0.
  [Model](https://huggingface.co/facebook/dinov2-small) ·
  [Source and license](https://github.com/facebookresearch/dinov2/blob/main/LICENSE).
  Browser-compatible ONNX conversion: [Xenova/dinov2-small](https://huggingface.co/Xenova/dinov2-small),
  pinned to revision `c2bb04a51fab207c420665f1946016107bffc701`.
- **Transformers.js 3.8.1**, Hugging Face, Apache License 2.0.
  [Source and license](https://github.com/huggingface/transformers.js/blob/3.8.1/LICENSE).
  Loaded on demand from jsDelivr. Includes ONNX Runtime Web;
  [Microsoft, MIT License](https://github.com/microsoft/onnxruntime/blob/main/LICENSE).
- Online reference photographs retain their individual **CC0** or **CC BY**
  licenses. Attribution and provenance are stored per photograph and displayed
  with the photograph. They are not relicensed under the application license.

The pretrained BioCLIP and DINOv2 image encoders are not fine-tuned. A separate
regularized linear reference metric is fitted offline using the 896 licensed
reference photographs. Its frozen weights and training provenance are recorded
in `image_metric.json` and embedded in the app. User photographs and the held-out
test photographs are not used to fit this metric. Photo attributions remain in
`BILDNACHWEISE.csv` inside `ribby_image_seed.zip` and the reference manifest.

A separate positive temperature scaling is fitted using photographer-disjoint
out-of-fold predictions of the same public reference photographs. Frozen
parameters and exact supported reference sets are recorded in
`image_calibration.json` and embedded in the app. Neither user photographs nor
independent test photographs are used to fit these parameters. This changes the
interpretation of scores, not the image encoders or species ranking. Method:
[Guo et al., ICML 2017](https://proceedings.mlr.press/v70/guo17a.html).
