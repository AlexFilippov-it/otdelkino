from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random

def setup_driver():
    """Настройка драйвера Chrome"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Работа в фоновом режиме
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Путь к ChromeDriver после установки через Homebrew
    service = Service('/opt/homebrew/bin/chromedriver')
    # Путь к Chrome после установки через Homebrew
    chrome_options.binary_location = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_total_pages(driver):
    """Определяет общее количество страниц в каталоге"""
    try:
        # Ждем появления элементов пагинации
        pagination_items = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'pagination__item'))
        )
        if pagination_items:
            page_numbers = []
            for item in pagination_items:
                try:
                    num = int(item.text.strip())
                    page_numbers.append(num)
                except ValueError:
                    continue
            if page_numbers:
                return max(page_numbers)
    except Exception as e:
        print(f"Ошибка при определении количества страниц: {str(e)}")
        
        # Добавим отладочную информацию
        try:
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            pagination = soup.find_all(class_='pagination__item')
            print(f"Найдено элементов пагинации: {len(pagination)}")
            if pagination:
                print("Тексты элементов пагинации:", [item.text.strip() for item in pagination])
        except Exception as debug_e:
            print(f"Ошибка при отладке пагинации: {debug_e}")
    
    return 1

def get_page_url(base_url, page):
    """Формирует URL страницы с учетом особенностей пагинации"""
    if page == 1:
        return base_url
    return f"{base_url}?PAGEN_1={page}"

def get_product_links(driver, base_url):
    """Получает ссылки на товары с использованием Selenium"""
    products_data = []
    page = 1
    
    # Определяем максимальное количество страниц для каждого раздела
    max_pages = {
        'https://otdelkino.ru/otdel_flooring/laminat/': 48,
        'https://otdelkino.ru/otdel_flooring/probkovoe_pokrytie/': 4,
        'https://otdelkino.ru/otdel_flooring/inzhenernaya-doska/': 8,
        'https://otdelkino.ru/otdel_flooring/parketnaya_doska/': 14,
        'https://otdelkino.ru/otdel_flooring/massivnaya_doska/': 1,
        'https://otdelkino.ru/otdel_flooring/terrasnaya_doska/': 2,
        'https://otdelkino.ru/otdel_flooring/linoleum/': 63,
        'https://otdelkino.ru/otdel_flooring/vinilovye_pokrytiya/': 17,
        'https://otdelkino.ru/otdel_flooring/kvartsvinilovye-poly-spc/': 48,
        'https://otdelkino.ru/otdel_flooring/specialnye_pvx_pokrytiya/': 1,
        'https://otdelkino.ru/otdel_flooring/kovrovye-pokrytiya-i-plitka/': 29,
        'https://otdelkino.ru/otdel_flooring/gryazezashhitnye_pokrytiya/': 1
        
    }
    
    try:
        while True:
            # Проверяем, не превысили ли максимальное количество страниц для текущего раздела
            if page > max_pages.get(base_url, 1):
                print(f"Достигнуто максимальное количество страниц ({max_pages.get(base_url)}) для раздела")
                break
                
            current_url = get_page_url(base_url, page)
            print(f"\nОбработка страницы {page}: {current_url}")
            
            driver.get(current_url)
            time.sleep(random.uniform(2, 4))
            
            # Проверяем наличие изображения 404
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            if soup.find('img', src='local/templates/otdelkino_main/images/404/cat_404.jpg'):
                print(f"Обнаружена страница 404, переходим к следующему разделу")
                break
            
            # Ждем загрузки товаров
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'slider-products__title-name'))
                )
            except Exception as e:
                print(f"Товары не найдены на странице {page}, переходим к следующему разделу")
                print(f"Ошибка: {str(e)}")
                break
            
            # Получаем HTML страницы и создаем объект BeautifulSoup
            products = soup.find_all('a', class_='slider-products__title-name')
            
            # Если товаров нет, переходим к следующему разделу
            if not products:
                print(f"Страница {page} пуста, переходим к следующему разделу")
                break
            
            for product in products:
                product_info = {
                    'url': 'https://otdelkino.ru' + product['href']
                }
                products_data.append(product_info)
                print(f"Найдена ссылка: {product_info['url']}")
            
            print(f"Собрано {len(products)} ссылок на странице {page}")
            
            # Переходим к следующей странице
            page += 1
            delay = random.uniform(2, 4)
            print(f"Пауза {delay:.1f} секунд перед следующей страницей...")
            time.sleep(delay)
                
        return products_data
        
    except Exception as e:
        print(f"Ошибка при получении данных: {e}")
        return products_data

def save_to_file(products):
    """Сохраняет только ссылки на товары в файл"""
    with open('products.txt', 'w', encoding='utf-8') as file:
        for product in products:
            file.write(f"{product['url']}\n")

if __name__ == "__main__":
    catalogs = [
        'https://otdelkino.ru/otdel_flooring/laminat/',
        'https://otdelkino.ru/otdel_flooring/probkovoe_pokrytie/',
        'https://otdelkino.ru/otdel_flooring/inzhenernaya-doska/',
        'https://otdelkino.ru/otdel_flooring/parketnaya_doska/',
        'https://otdelkino.ru/otdel_flooring/massivnaya_doska/',
        'https://otdelkino.ru/otdel_flooring/terrasnaya_doska/',
        'https://otdelkino.ru/otdel_flooring/linoleum/',
        'https://otdelkino.ru/otdel_flooring/vinilovye_pokrytiya/',
        'https://otdelkino.ru/otdel_flooring/kvartsvinilovye-poly-spc/',
        'https://otdelkino.ru/otdel_flooring/specialnye_pvx_pokrytiya/',
        'https://otdelkino.ru/otdel_flooring/kovrovye-pokrytiya-i-plitka/',
        'https://otdelkino.ru/otdel_flooring/gryazezashhitnye_pokrytiya/'
    ]
    
    all_products = []
    driver = setup_driver()
    
    try:
        # Обрабатываем каждый каталог
        for catalog_url in catalogs:
            print(f"\nОбработка каталога: {catalog_url}")
            products = get_product_links(driver, catalog_url)
            if products:
                all_products.extend(products)
                print(f"Добавлено {len(products)} товаров из каталога")
            
            # Увеличенная задержка между каталогами
            if catalog_url != catalogs[-1]:
                delay = random.uniform(5, 10)
                print(f"Пауза {delay:.1f} секунд перед следующим каталогом...")
                time.sleep(delay)
        
        print(f'\nВсего найдено товаров: {len(all_products)}')
        save_to_file(all_products)
        
    finally:
        driver.quit() 