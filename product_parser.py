from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import random
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import csv
import yaml  # Добавляем импорт PyYAML
from xml.etree import ElementTree as ET
from xml.dom import minidom
import os
from urllib.parse import urlparse
import hashlib

def get_product_details(url, timeout=20):
    driver = None
    try:
        # Настройка Chrome с расширенной маскировкой
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-gpu')
        
        # Расширенные заголовки для имитации реального браузера
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        chrome_options.add_argument('--accept-language=ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Дополнительные параметры для маскировки
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')
        
        service = Service('/opt/homebrew/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Маскируем WebDriver
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
            '''
        })
        
        driver.set_page_load_timeout(timeout)
        driver.set_script_timeout(timeout)
        wait = WebDriverWait(driver, timeout)
        
        print(f"\nПолучаем информацию о товаре: {url}")
        time.sleep(random.uniform(2, 4))
        
        try:
            driver.get(url)
            scroll_height = random.randint(300, 700)
            driver.execute_script(f"window.scrollTo(0, {scroll_height});")
            time.sleep(random.uniform(1, 2))
        except TimeoutException:
            print(f"Превышено время ожидания загрузки страницы: {url}")
            return None
        
        product_info = {}
        
        # Получаем название товара
        try:
            product_info['name'] = driver.find_element(By.CLASS_NAME, 'page-detail__title').text.strip()
        except:
            print("Не удалось получить название товара")
            product_info['name'] = "Не указано"
        
        # Получаем ссылки на изображения и видео
        images = []
        youtube_links = []
        
        # Сначала ищем все изображения в слайдере
        img_elements = driver.find_elements(By.CSS_SELECTOR, '.page-detail__images-slider-item-img')
        
        # Если изображения в слайдере не найдены, ищем в основном блоке
        if not img_elements:
            print("Изображения в слайдере не найдены, ищем в основном блоке...")
            img_elements = driver.find_elements(By.CSS_SELECTOR, '.js-page-detail__images-main-img')
        
        # Если все еще нет изображений, выводим предупреждение
        if not img_elements:
            print("Предупреждение: не найдены изображения ни в слайдере, ни в основном блоке")
        
        # Обрабатываем первые 3 изображения из найденных
        for img in img_elements[:3]:
            try:
                full_image = img.get_attribute('data-full-image')
                big_image = img.get_attribute('data-big-image')
                src_image = img.get_attribute('src')
                
                image_url = full_image or big_image or src_image
                
                if image_url:
                    if 'youtube.com' in image_url or 'youtu.be' in image_url:
                        youtube_links.append(image_url)
                        print(f"Найдена ссылка на YouTube: {image_url}")
                    else:
                        if image_url.startswith('/'):
                            image_url = 'https://otdelkino.ru' + image_url
                        
                        print(f"Обработка изображения {len(images) + 1}: {image_url}")
                        downloaded_filename = download_image(image_url)
                        if downloaded_filename:
                            images.append(downloaded_filename)
                            print(f"Успешно сохранено изображение {len(images)}")
            except Exception as e:
                print(f"Ошибка при обработке медиа: {str(e)}")
                continue
        
        product_info['images'] = images
        product_info['youtube_links'] = youtube_links
        
        print(f"Итого найдено: изображений - {len(images)}, YouTube ссылок - {len(youtube_links)}")
        
        # Получаем цену
        try:
            price_element = driver.find_element(By.ID, 'productPrice')
            product_info['price'] = price_element.text.strip()
        except:
            print("Не удалось получить цену")
            product_info['price'] = "Не указано"
        
        # Получаем количество в упаковке
        try:
            package_count = driver.find_element(By.CLASS_NAME, 'js-page-detail__main-packages-count-result-value')
            product_info['package_count'] = package_count.text.strip()
        except:
            product_info['package_count'] = 'Не указано'
        
        # Получаем описание
        try:
            description = driver.find_element(By.CLASS_NAME, 'js-page-detail__description-text')
            product_info['description'] = description.text.strip()
        except:
            product_info['description'] = 'Описание отсутствует'
        
        # Получаем breadcrumbs
        try:
            breadcrumbs = []
            breadcrumb_items = driver.find_elements(By.CSS_SELECTOR, '.breadcrumbs-list__item')
            for item in breadcrumb_items:
                try:
                    link = item.find_element(By.CSS_SELECTOR, '.breadcrumbs-list__item-link')
                    text = link.text.strip()
                    if not text:
                        text = item.find_element(By.CSS_SELECTOR, 'span.breadcrumbs-list__item-link').text.strip()
                    if text and text != 'Главная':
                        breadcrumbs.append(text)
                except:
                    continue
            
            product_info['breadcrumbs'] = breadcrumbs
            print(f"Найдены разделы: {' > '.join(breadcrumbs)}")
        except Exception as e:
            print(f"Не удалось получить breadcrumbs: {str(e)}")
            product_info['breadcrumbs'] = []
        
        # Получаем характеристики
        characteristics = {}
        try:
            info_items = driver.find_elements(By.CLASS_NAME, 'page-detail__main-info-item')
            for item in info_items:
                try:
                    name = item.find_element(By.CLASS_NAME, 'page-detail__main-info-item-name').text.strip()
                    value = item.find_element(By.CLASS_NAME, 'page-detail__main-info-item-value').text.strip()
                    characteristics[name] = value
                except:
                    continue
        except:
            print("Не удалось получить характеристики")
        
        product_info['characteristics'] = characteristics
        
        return product_info
        
    except WebDriverException as e:
        print(f"Ошибка браузера при получении информации о товаре: {str(e)}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка при получении информации о товаре: {str(e)}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                print(f"Ошибка при закрытии драйвера: {str(e)}")

def get_all_characteristics(products_info):
    characteristics = set()
    for product in products_info:
        if 'characteristics' in product:
            characteristics.update(product['characteristics'].keys())
    return sorted(list(characteristics))

def download_image(url, img_dir='img', timeout=10):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        img_dir = os.path.join(current_dir, img_dir)
        
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
            print(f"Создана директория для изображений: {img_dir}")
        
        if url.startswith('/'):
            url = 'https://otdelkino.ru' + url
        
        parsed_url = urlparse(url)
        ext = os.path.splitext(parsed_url.path)[1]
        if not ext:
            ext = '.jpg'
        
        filename = hashlib.md5(url.encode()).hexdigest() + ext
        csv_filename = f"unic/img/{filename}"
        filepath = os.path.join(img_dir, filename)
        
        if os.path.exists(filepath):
            print(f"Изображение уже существует: {filename}")
            return csv_filename
        
        print(f"Скачиваем изображение с URL: {url}")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        service = Service('/opt/homebrew/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)
        
        try:
            driver.get(url)
            img_base64 = driver.execute_script("""
                return new Promise((resolve, reject) => {
                    const timeoutId = setTimeout(() => reject('Timeout'), 5000);
                    const img = new Image();
                    img.onload = function() {
                        clearTimeout(timeoutId);
                        const canvas = document.createElement('canvas');
                        canvas.width = this.width;
                        canvas.height = this.height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(this, 0, 0);
                        resolve(canvas.toDataURL('image/jpeg', 0.8));
                    };
                    img.onerror = () => {
                        clearTimeout(timeoutId);
                        reject('Failed to load image');
                    };
                    img.src = arguments[0];
                });
            """, url)
            
            import base64
            img_data = base64.b64decode(img_base64.split(',')[1])
            
            with open(filepath, 'wb') as f:
                f.write(img_data)
            
            print(f"Скачано изображение: {filename}")
            return csv_filename
            
        except TimeoutException:
            print(f"Превышено время ожидания при скачивании изображения: {url}")
            return None
        except Exception as e:
            print(f"Ошибка при скачивании изображения {url}: {str(e)}")
            return None
        finally:
            driver.quit()
    
    except Exception as e:
        print(f"Ошибка при обработке изображения {url}: {str(e)}")
        return None

def save_to_csv(products_info, filename='products_info.csv'):
    if not products_info:
        print("Нет данных для сохранения в CSV файл")
        return
    
    image_headers = ['image_1', 'image_2', 'image_3']
    
    max_youtube_links = max(len(product.get('youtube_links', [])) for product in products_info)
    youtube_headers = [f'video_{i+1}' for i in range(max_youtube_links)]
    
    max_breadcrumbs = max(len(product.get('breadcrumbs', [])) for product in products_info)
    breadcrumb_headers = [f'category_{i+1}' for i in range(max_breadcrumbs)]
    
    all_characteristics = get_all_characteristics(products_info)
    
    fieldnames = ['name', 'price', 'package_count', 'description'] + \
                breadcrumb_headers + \
                image_headers + \
                youtube_headers + \
                all_characteristics
    
    try:
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            writer.writerow(fieldnames)
            
            for product in products_info:
                row = []
                row.append(product.get('name', ''))
                row.append(product.get('price', ''))
                row.append(product.get('package_count', ''))
                row.append(product.get('description', ''))
                
                breadcrumbs = product.get('breadcrumbs', [])
                for i in range(max_breadcrumbs):
                    row.append(breadcrumbs[i] if i < len(breadcrumbs) else '')
                
                images = product.get('images', [])
                for i in range(3):
                    row.append(images[i] if i < len(images) else '')
                
                youtube_links = product.get('youtube_links', [])
                for i in range(max_youtube_links):
                    row.append(youtube_links[i] if i < len(youtube_links) else '')
                
                characteristics = product.get('characteristics', {})
                for char in all_characteristics:
                    row.append(characteristics.get(char, ''))
                
                writer.writerow(row)
        
        print(f"\nИнформация о товарах сохранена в файл {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении в CSV файл: {str(e)}")
        raise

def save_to_yml(products_info, filename='products_info.yml'):
    """Сохраняет информацию о товарах в YAML файл"""
    if not products_info:
        print("Нет данных для сохранения в YAML файл")
        return
    
    # Подготавливаем структуру для YAML
    yaml_data = {
        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'shop': {
            'name': 'Otdelkino',
            'company': 'Otdelkino',
            'url': 'https://otdelkino.ru'
        },
        'currencies': {
            'currency': {
                'id': 'RUR',
                'rate': '1'
            }
        },
        'categories': {
            'category': 'Ламинат'
        },
        'offers': []
    }
    
    # Добавляем товары
    for product in products_info:
        offer = {
            'name': product.get('name', ''),
            'price': product.get('price', '').replace(' ', '').replace('руб.', ''),
            'currencyId': 'RUR',
            'categoryId': 'Ламинат',
            'images': product.get('images', []),
            'description': product.get('description', ''),
            'package_count': product.get('package_count', ''),
            'characteristics': product.get('characteristics', {})
        }
        yaml_data['offers'].append(offer)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"\nИнформация о товарах сохранена в файл {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении в YAML файл: {str(e)}")
        raise

def save_to_xml(products_info, filename='products_info.xml'):
    """Сохраняет информацию о товарах в XML файл"""
    if not products_info:
        print("Нет данных для сохранения в XML файл")
        return
    
    # Создаем корневой элемент
    root = ET.Element('yml_catalog')
    root.set('date', time.strftime('%Y-%m-%d %H:%M:%S'))
    
    # Создаем элемент shop
    shop = ET.SubElement(root, 'shop')
    
    # Добавляем информацию о магазине
    ET.SubElement(shop, 'name').text = 'Otdelkino'
    ET.SubElement(shop, 'company').text = 'Otdelkino'
    ET.SubElement(shop, 'url').text = 'https://otdelkino.ru'
    
    # Добавляем валюты
    currencies = ET.SubElement(shop, 'currencies')
    currency = ET.SubElement(currencies, 'currency')
    currency.set('id', 'RUR')
    currency.set('rate', '1')
    
    # Добавляем категории
    categories = ET.SubElement(shop, 'categories')
    category = ET.SubElement(categories, 'category')
    category.set('id', '1')
    category.text = 'Ламинат'
    
    # Добавляем товары
    offers = ET.SubElement(shop, 'offers')
    
    for i, product in enumerate(products_info, 1):
        offer = ET.SubElement(offers, 'offer')
        offer.set('id', str(i))
        offer.set('available', 'true')
        
        # Добавляем основную информацию о товаре
        ET.SubElement(offer, 'name').text = product.get('name', '')
        ET.SubElement(offer, 'price').text = product.get('price', '').replace(' ', '').replace('руб.', '')
        ET.SubElement(offer, 'currencyId').text = 'RUR'
        ET.SubElement(offer, 'categoryId').text = '1'
        
        # Добавляем изображения
        for img_url in product.get('images', []):
            ET.SubElement(offer, 'picture').text = img_url
        
        # Добавляем описание
        ET.SubElement(offer, 'description').text = product.get('description', '')
        
        # Добавляем количество в упаковке
        ET.SubElement(offer, 'package_count').text = product.get('package_count', '')
        
        # Добавляем характеристики
        params = product.get('characteristics', {})
        for param_name, param_value in params.items():
            param = ET.SubElement(offer, 'param')
            param.set('name', param_name)
            param.text = param_value
    
    # Создаем строку XML с отступами
    xml_str = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent='  ')
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        print(f"\nИнформация о товарах сохранена в файл {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении в XML файл: {str(e)}")
        raise

def main():
    try:
        with open('products.txt', 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
            print(f"Найдено {len(urls)} ссылок для обработки")
    except Exception as e:
        print(f"Ошибка при чтении файла с URL: {str(e)}")
        return
    
    all_products_info = []
    
    for i, url in enumerate(urls, 1):
        try:
            print(f"\nОбработка товара {i} из {len(urls)}")
            product_info = get_product_details(url)
            
            if product_info:
                all_products_info.append(product_info)
                print(f"Успешно обработан товар: {product_info['name']}")
            else:
                print(f"Не удалось получить информацию о товаре: {url}")
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Ошибка при обработке товара {url}: {str(e)}")
            continue
    
    if all_products_info:
        print(f"\nВсего успешно обработано товаров: {len(all_products_info)}")
        save_to_csv(all_products_info)
    else:
        print("Нет данных для сохранения")

if __name__ == '__main__':
    main() 