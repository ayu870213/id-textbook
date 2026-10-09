"""사이트 주소 QR 코드 만들기 (가운데에 '감염내과 / 참고서').

  python tools/make_qr.py            → qr/감염내과참고서_QR.png
필요: pip install qrcode pillow opencv-python-headless (확인용)
"""
import os, sys

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'https://ayu870213.github.io/id-textbook/'
LINES = ['감염내과', '참고서']
INK = '#1f5a45'  # 사이트 accent 색
FONT = r'C:\Windows\Fonts\malgunbd.ttf'
OUT = os.path.join(ROOT, 'qr', '감염내과참고서_QR.png')


def make():
    # H: 약 30%까지 가려져도 읽힘. 가운데 글자 상자는 그보다 훨씬 작게 둔다.
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=24, border=4)
    qr.add_data(URL); qr.make(fit=True)
    img = qr.make_image(fill_color=INK, back_color='white').convert('RGB')
    W = img.size[0]
    n = qr.modules_count

    # 가운데 상자: QR 폭의 약 30%(면적 약 9%), 모듈 칸에 맞춤
    box_mod = round(n * 0.30) | 1
    box = box_mod * qr.box_size
    x0 = y0 = (W - box) // 2
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x0 + box, y0 + box], radius=box // 8, fill='white', outline=INK, width=qr.box_size // 3)

    size = box // 4
    font = ImageFont.truetype(FONT, size)
    while max(d.textlength(t, font=font) for t in LINES) > box * 0.82:
        size -= 2; font = ImageFont.truetype(FONT, size)
    gap = size // 5
    total = len(LINES) * size + (len(LINES) - 1) * gap
    y = y0 + (box - total) // 2 - size // 10
    for t in LINES:
        d.text((W // 2, y), t, font=font, fill=INK, anchor='mt')
        y += size + gap

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    return OUT


def check(path):
    """원본 크기와 작게 줄인 크기(인쇄·화면 축소 상황)에서 모두 읽히는지 확인."""
    import cv2, numpy as np
    img = Image.open(path).convert('RGB')
    det = cv2.QRCodeDetector()
    for w in (img.size[0], 300, 200):
        arr = np.array(img.resize((w, w), Image.LANCZOS))
        data, _, _ = det.detectAndDecode(arr)
        print(f'  {w}px: {"읽힘" if data == URL else "읽히지 않음"} ({data or "-"})')
        if data != URL:
            sys.exit(1)


if __name__ == '__main__':
    p = make()
    print('저장:', p)
    check(p)
