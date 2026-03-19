import os
import glob

folder = r"D:\Лаба\РП дисциплин и практик (маг ПФ) 2026 оч-заоч\Факультативы"

if not folder:
    folder = input("Путь к папке: ") or "."

for file in glob.glob(os.path.join(folder, "*.docx")):
    dir_name = os.path.dirname(file)
    base, ext = os.path.splitext(os.path.basename(file))

    # pos = base.find("РП практики")
    pos = base.find("РП дисциплины")
    if pos == -1:
        print(f"Пропущен (нет 'РП дисциплины'): {base}{ext}")
        continue

    new_name = base[pos:] + ext
    new_path = os.path.join(dir_name, new_name)

    if new_path == file:
        print(f"Уже в нужном формате: {base}{ext}")
        continue

    os.rename(file, new_path)
    print(f"{base}{ext} -> {new_name}")