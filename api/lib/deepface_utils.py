import cv2
import numpy as np
from deepface.commons import image_utils
from PIL import Image
from retinaface import RetinaFace  # this is not a must dependency


def get_alignment_angle_arctan2(left_eye, right_eye):
    # this function aligns given face in img based on left and right eye coordinates
    """
    The left_eye is the eye to the left of the viewer,
    left_eye_x, left_eye_y = left_eye
    i.e., right eye of the person in the image.
    right_eye_x, right_eye_y = right_eye
    The top-left point of the frame is (0, 0).
    """
    # -----------------------
    return float(
        np.degrees(
            # find rotation direction
            np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0])
        )
    )


def alignment_procedure(img, left_eye, right_eye):
    angle = get_alignment_angle_arctan2(left_eye, right_eye)
    img = Image.fromarray(img)
    img = np.array(img.rotate(angle))
    return img


def detect_retinaface(backend_model, img, align=True):
    resp = []

    obj = RetinaFace.detect_faces(img, model=backend_model, threshold=0.9)

    if isinstance(obj, dict):
        for face_idx in obj.keys():
            identity = obj[face_idx]
            facial_area = identity["facial_area"]

            y = facial_area[1]
            h = facial_area[3] - y
            x = facial_area[0]
            w = facial_area[2] - x
            img_region = [x, y, w, h]
            confidence = identity["score"]

            # detected_face = img[int(y):int(y+h), int(x):int(x+w)] #opencv
            detected_face = img[
                facial_area[1] : facial_area[3], facial_area[0] : facial_area[2]
            ]

            if align:
                landmarks = identity["landmarks"]
                left_eye = landmarks["left_eye"]
                right_eye = landmarks["right_eye"]
                # nose = landmarks["nose"]
                # mouth_right = landmarks["mouth_right"]
                # mouth_left = landmarks["mouth_left"]

                detected_face = alignment_procedure(detected_face, right_eye, left_eye)

            resp.append((detected_face, img_region, confidence, identity["landmarks"]))

    return resp


# This should be a replacement for functions.extract_faces()
# that also returns the landmarks. This will then be followed
# by stand-in code for the rest of DeepFace.represent()
def extract_face_regions(
    backend_model,
    frontend_model,
    img,
    align=True,
    enforce_detection=False,
    grayscale=False,
):
    extracted_faces = []

    img = image_utils.load_image(img)[0]
    # Only used if no face sub-images are detected
    img_region = [0, 0, img.shape[1], img.shape[0]]

    target_size = frontend_model.input_shape

    face_objs = detect_retinaface(backend_model, img, align)

    if len(face_objs) == 0 and enforce_detection is True:
        raise ValueError(
            "Face could not be detected. "
            " Please confirm that the picture is a face photo "
            + "or consider to set enforce_detection param to False."
        )

    if len(face_objs) == 0 and enforce_detection is False:
        face_objs = [(img, img_region, 0, {})]

    for current_img, current_region, confidence, landmarks in face_objs:
        if confidence > 0 and current_img.shape[0] > 0 and current_img.shape[1] > 0:
            if grayscale is True:
                current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)

            # resize and padding
            if current_img.shape[0] > 0 and current_img.shape[1] > 0:
                factor_0 = target_size[0] / current_img.shape[0]
                factor_1 = target_size[1] / current_img.shape[1]
                factor = min(factor_0, factor_1)

                dsize = (
                    int(current_img.shape[1] * factor),
                    int(current_img.shape[0] * factor),
                )
                current_img = cv2.resize(current_img, dsize)

                diff_0 = target_size[0] - current_img.shape[0]
                diff_1 = target_size[1] - current_img.shape[1]
                if grayscale is False:
                    # Put the base image in the middle of the padded image
                    current_img = np.pad(
                        current_img,
                        (
                            (diff_0 // 2, diff_0 - diff_0 // 2),
                            (diff_1 // 2, diff_1 - diff_1 // 2),
                            (0, 0),
                        ),
                        "constant",
                    )
                else:
                    current_img = np.pad(
                        current_img,
                        (
                            (diff_0 // 2, diff_0 - diff_0 // 2),
                            (diff_1 // 2, diff_1 - diff_1 // 2),
                        ),
                        "constant",
                    )

            # double check: if target image is not still the same size with target.
            if current_img.shape[0:2] != target_size:
                current_img = cv2.resize(current_img, target_size)

            # normalizing the image pixels
            img_pixels = np.asarray(current_img, dtype="uint8")
            img_pixels = np.expand_dims(img_pixels, axis=0)
            img_pixels = img_pixels / 255

            # int cast is for the exception - object of type 'float32' is not
            # JSON serializable
            region_obj = {
                "x": round(float(current_region[0]), 2),
                "y": round(float(current_region[1]), 2),
                "w": round(float(current_region[2]), 2),
                "h": round(float(current_region[3]), 2),
            }

            extracted_face = [img_pixels, region_obj, confidence, landmarks]
            extracted_faces.append(extracted_face)

    if len(extracted_faces) == 0 and enforce_detection is True:
        raise ValueError(
            f"Detected face shape is {img.shape}. Consider to set enforce_detection arg to False."
        )

    return extracted_faces
