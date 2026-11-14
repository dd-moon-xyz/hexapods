import contextlib
import json
import math
import sys


MODEL = '/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk'


def person_height(boxes, scores, classes, threshold=0.6):
    # SSD boxes are normalized y0,x0,y1,x1; COCO person is class zero.
    heights = [
        max(0.0, min(1.0, float(box[2])) - max(0.0, float(box[0])))
        for box, score, category in zip(boxes, scores, classes)
        if math.isfinite(float(score)) and score >= threshold and category == 0
        and all(math.isfinite(float(value)) for value in box)
        and box[2] > box[0] and box[3] > box[1]
    ]
    return max(heights, default=0.0)


def main():
    # Picamera2 and its native dependencies use the OS Python ABI, not uv's 3.14.
    output = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        from picamera2 import Picamera2
        from picamera2.devices import IMX500

        imx500 = IMX500(MODEL)
        camera = Picamera2(imx500.camera_num)
        try:
            camera.configure(camera.create_video_configuration(
                main={'size': (640, 480)},
                controls={'FrameRate': imx500.network_intrinsics.inference_rate or 26}, buffer_count=6,
            ))
            camera.start()
            print('Person camera started: SSD MobileNetV2, confidence >= 0.60', flush=True)
            while True:
                metadata = camera.capture_metadata()
                tensors = imx500.get_outputs(metadata, add_batch=True)
                if tensors is None:
                    continue
                height = person_height(tensors[0][0], tensors[1][0], tensors[2][0])
                print(json.dumps({'height': height}), file=output, flush=True)
        finally:
            camera.close()
            if imx500.device_fd is not None:
                imx500.device_fd.close()


if __name__ == '__main__':
    main()
