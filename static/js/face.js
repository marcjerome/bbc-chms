// Face recognition setup shared by the kiosk and the enrollment page. Everything runs in this browser,
// offline: the models are served by the church computer (static/models/face/).
window.flockFace = {
  ready: null,
  /** Load the models once. Uses the graphics chip (WebGL) when there is one, otherwise the processor. */
  load(models) {
    this.ready ??= (async () => {
      const tf = faceapi.tf;
      for (const backend of ["webgl", "cpu"]) {
        try { if (await tf.setBackend(backend)) break; } catch (e) { /* try the next one */ }
      }
      await tf.ready();
      await faceapi.nets.tinyFaceDetector.loadFromUri(models);
      await faceapi.nets.faceLandmark68TinyNet.loadFromUri(models);
      await faceapi.nets.faceRecognitionNet.loadFromUri(models);
      return tf.getBackend();
    })();
    return this.ready;
  },
};
