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

# загружаем уже собранные хеши (если файл существует)
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
    # 1. Начать новый тест
    start_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@title='Пройти тестирование']")))
    start_btn.click()

    # 2. Выбрать специальность
    spec_xpath = "//button[contains(., 'Фармацевтическая химия и фармакогнозия')]"
    spec_button = wait.until(EC.element_to_be_clickable((By.XPATH, spec_xpath)))

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", spec_button)
    time.sleep(1)  # Даем сайту "осознать" прокрутку

    try:
        spec_button.click()
    except:
        # Если обычный клик не прошел, пробуем JS, но СТРОГО после прокрутки
        driver.execute_script("arguments[0].click();", spec_button)

    # Ждем, пока кнопка реально исчезнет или сменится состояние страницы
    wait.until(EC.invisibility_of_element_located((By.XPATH, spec_xpath)))
    time.sleep(1)

    # 3. Переключаемся на новую вкладку, где загрузится тест
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(7)

    # 4. Начать тестирование
    start_question = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
        (By.XPATH, "//button[.//*[contains(text(),'Перейти к первому вопросу')]]")
    ))
    start_question.click()
    print("Кнопка нажата, ждём question_list...")
    time.sleep(5)
    print(f"URL после нажатия: {driver.current_url}")
    print(f"Заголовок страницы: {driver.title}")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "question_list"))
    )
    print("question_list найден!")

    # 5. Завершить тест
    finish_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
        (By.XPATH, "//button[.//*[contains(text(),'Завершить тестирование')]]")
    ))
    finish_btn.click()
    finish_confirm_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
        (By.XPATH, "//button[.//*[contains(text(),'Все равно завершить')]]")
    ))
    driver.execute_script("arguments[0].scrollIntoView(true);", finish_confirm_btn)
    time.sleep(0.5)
    finish_confirm_btn.click()

    # 6. Ожидание страницы результатов
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table.qList"))
    )
    print("table.qList найдена!")

    # 7. Клик по первому видимому триггеру в таблице
    all_triggers = wait.until(EC.presence_of_all_elements_located((
        By.CSS_SELECTOR, "td.qAnswer span.xforms-trigger"
    )))
    # Первые 2 — шаблонные (нулевой размер), третий (индекс 3) — первая реальная строка
    visible_triggers = [t for t in all_triggers if t.size['width'] > 0]
    first_trigger = visible_triggers[0]
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_trigger)
    time.sleep(0.5)
    ActionChains(driver).move_to_element(first_trigger).click().perform()
    print("Клик по первому вопросу совершен!")

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
            print("Достигли последнего вопроса, выходим")
            break

        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(0.5)
