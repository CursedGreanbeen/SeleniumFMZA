from docx2pdf import convert
from pathlib import Path

input_dir = Path(r"D:\Лаба\Промышленная фармация 26 год\РП дисциплин и практик (маг ПФ) 2026 очн\Вариативная часть")
output_dir = Path(r"D:\Лаба\Промышленная фармация 26 год (pdf)\РП дисциплин и практик (маг ПФ) 2026 очн\Вариативная часть")
output_dir.mkdir(parents=True, exist_ok=True)

for docx_file in input_dir.glob("*.docx"):
    pdf_file = output_dir / (docx_file.stem + ".pdf")

    # Если PDF уже существует — пропускаем (можно заменить на другое поведение)
    if pdf_file.exists():
        print(f"Пропущен (уже есть): {pdf_file.name}")
        continue

    try:
        print(f"Конвертирую: {docx_file.name}")
        convert(str(docx_file), str(pdf_file))
    except Exception as e:
        print(f"Ошибка при конвертации {docx_file.name}: {e}")
        # можно добавить логирование или просто игнорировать
        continue
