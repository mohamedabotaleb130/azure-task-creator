def qr_matrix(data):
    import qrcode

    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.get_matrix()


def draw_qr_on_canvas(canvas, matrix, scale=8):
    canvas.delete("all")
    size = len(matrix) * scale
    canvas.config(width=size, height=size)
    for y, row in enumerate(matrix):
        for x, cell in enumerate(row):
            if cell:
                canvas.create_rectangle(
                    x * scale,
                    y * scale,
                    (x + 1) * scale,
                    (y + 1) * scale,
                    fill="#0f172a",
                    outline="#0f172a",
                )
