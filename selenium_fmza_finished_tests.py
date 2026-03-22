from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import hashlib
import csv
import time


def find_next_btn():
    for attempt in range(3):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span#next"))
            )
            container = driver.find_element(By.CSS_SELECTOR, "span#next")
            parent_div = container.find_element(By.XPATH, "./ancestor::div[contains(@class,'button100')]")
            if "disabled" in parent_div.get_attribute("class").split():
                return None
            btn = container.find_element(By.CSS_SELECTOR, "span.value button")
            return btn
        except StaleElementReferenceException:
            print(f"Stale при поиске next_btn, попытка {attempt+1}/3")
            time.sleep(0.5)
    raise Exception("Не удалось найти next_btn после 3 попыток")


driver = webdriver.Chrome()
wait = WebDriverWait(driver, 10)
base_url = "https://selftest.mededtech.ru/"
driver.get(base_url)

try:
    # Ожидание появления формы входа
    username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    username_field.send_keys("username")

    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys("password")

    # Нажатие кнопки входа
    submit_button = driver.find_element(By.CSS_SELECTOR, "input.login-button")
    submit_button.click()

    # Ждём, пока загрузится основная страница
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@title='Пройти тестирование']")))
    print("Авторизация успешна")
except Exception as e:
    print("Ошибка при авторизации:", e)
    driver.quit()
    exit(1)

main_window = driver.current_window_handle  # дескриптор главного окна
collected = set()
output_file = "answers.csv"

# загружаем уже собранные хеши
try:
    with open(output_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            collected.add(row["question_hash"])
except FileNotFoundError:
    pass

with open(output_file, "a", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "question_hash", "question_num", "question_html", "correct_answer", "all_answers"
    ])
    if not collected:
        writer.writeheader()

    print(f"=== Начало итерации. Собрано: {len(collected)-1} ===")
    time.sleep(5)

    # 2. Собрать все кнопки "Перейти к тесту"
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[title='Перейти к тесту']")))
    test_links = driver.find_elements(By.CSS_SELECTOR, "div[title='Перейти к тесту'] a")
    test_urls = [a.get_attribute("href") for a in test_links]
    print(f"Найдено вариантов: {len(test_urls)}")

    for url in test_urls:
        print(f"Открываем вариант: {url}")
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])

        # Ждём загрузки первого вопроса
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".question_options"))
        )

        # 8. Обработка каждого вопроса
        while True:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".question_options")
            ))
            q_html = driver.find_element(By.CSS_SELECTOR, "span.xforms-output.testQuestion").text.strip()
            q_hash = hashlib.md5(q_html.encode("utf-8")).hexdigest()

            if q_hash not in collected:
                all_tds = driver.find_elements(By.CSS_SELECTOR, "td.testAnswer")
                correct_answer = "NOT_FOUND"
                answers = []
                for td in all_tds:
                    text = td.text.strip()
                    if not text:
                        continue
                    if "correct_answer" in td.get_attribute("class"):
                        correct_answer = text
                        answers.insert(0, f"[+] {text}")
                    else:
                        answers.append(text)
                all_answers_str = " | ".join(answers)

                # сохранить
                writer.writerow({
                    "question_hash": q_hash,
                    "question_num": "",
                    "question_html": q_html,
                    "correct_answer": correct_answer,
                    "all_answers": all_answers_str
                })
                f.flush()
                collected.add(q_hash)

            next_btn = find_next_btn()
            if next_btn is None:
                print("Кнопка disabled — последний вопрос, выходим")
                break

            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(0.5)

        # Закрыть вкладку с вариантом, вернуться на главную
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        print("Вариант обработан, переходим к следующему")
        time.sleep(0.5)
