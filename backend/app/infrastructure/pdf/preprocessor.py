"""
Prétraitement d'image pour les pages scannées, avant OCR.

Deskew (redressement) : calcule l'angle d'inclinaison dominant du texte
sur la page et fait pivoter l'image pour le corriger. Essentiel pour les
PDF "inclinés" ou "photographiés" mentionnés dans le besoin initial.
"""

import cv2
import numpy as np


def deskew_image(image: np.ndarray) -> np.ndarray:
    """Redresse une image (tableau numpy BGR) si elle est inclinée."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)

    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))

    if len(coords) < 20:
        # Pas assez de pixels de texte détectés -- on ne touche pas à l'image,
        # mieux vaut ne rien casser que de "corriger" une image quasi vide.
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # On ignore les micro-angles (bruit de mesure) pour ne pas introduire
    # une rotation inutile sur une page déjà droite.
    if abs(angle) < 0.5:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )


def pdf_page_to_cv_image(page, zoom: float = 2.0) -> np.ndarray:
    """Convertit une page PyMuPDF en image OpenCV (BGR).
    zoom=2.0 double la résolution -- utile car l'OCR est plus précis sur
    des images nettes, surtout pour des scans de mauvaise qualité."""
    matrix = page.get_pixmap(matrix=[zoom, 0, 0, zoom, 0, 0])
    img_array = np.frombuffer(matrix.samples, dtype=np.uint8).reshape(
        matrix.height, matrix.width, matrix.n
    )
    if matrix.n == 4:  # RGBA -> BGR
        return cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

def enhance_scan_quality(image: np.ndarray) -> np.ndarray:
    """Améliore un scan de mauvaise qualité (vieux document, contraste
    faible, grain) SANS binariser -- docTR est un modèle de deep learning
    qui reste plus précis sur une image en nuances de gris/couleur qu'en
    noir et blanc pur (contrairement à Tesseract).

    Deux opérations, dans cet ordre précis (l'ordre compte) :
    1. Débruitage -- réduit le grain du scan sans flouter le texte.
    2. CLAHE (contraste adaptatif local) -- renforce le contraste zone par
       zone, utile sur un scan avec un éclairage inégal (typique d'un vieux
       document photographié plutôt que scanné à plat).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)