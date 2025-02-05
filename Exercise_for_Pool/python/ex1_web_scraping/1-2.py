from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import random
import re
import pandas as pd
import time


def set_user_agent(driver):
    """ユーザーエージェントをランダムに設定する関数"""
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.",
    ]
    random_user_agent = random.choice(user_agents)
    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride", {"userAgent": random_user_agent}
    )
    return driver


def generate_url(base_url, driver):
    """指定されたページから店舗のURLを収集"""

    driver.get(base_url)
    driver.implicitly_wait(10)
    time.sleep(3)

    while True:
        # 店舗のURLを取得
        new_urls = [
            elem.get_attribute("href")
            for elem in driver.find_elements(By.CLASS_NAME, "style_titleLink__oiHVJ")
        ]

        if not new_urls:
            print("店舗のページを取得できませんでした。")
            break

        for url in new_urls:
            yield url

        try:
            driver.get(base_url)
            next_page = driver.find_element(
                By.XPATH, "//img[@alt[contains(., '次')]]/parent::a"
            )

            next_page.click()
            print("次のページに移りました。")
            time.sleep(3)
            base_url = driver.current_url

        except NoSuchElementException as e:
            print("次のページボタンが見つかりませんでした。")
            break


def get_infomation(url, driver):
    """店舗の詳細情報を収集"""
    driver.get(url)
    driver.implicitly_wait(10)
    try:
        # 情報を取得
        info_table = driver.find_element(By.ID, "info-table")
        name = info_table.find_element(By.ID, "info-name").text
        email = ""
        phone = info_table.find_element(
            By.CSS_SELECTOR, "#info-phone > td > ul > li > span.number"
        ).text

        address_full = info_table.find_element(
            By.CSS_SELECTOR,
            "#info-table > table > tbody > tr:nth-child(3) > td > p > span.region",
        ).text

        # 住所を都道府県、市区町村、番地に分割
        m = re.match(r"([^\s]+[都道府県])([^\s]+[市区町村])(.+)", address_full)
        prefecture, city, street = m.groups() if m else ("", "", "")

        building = info_table.find_elements(
            By.CSS_SELECTOR,
            "#info-table > table > tbody > tr:nth-child(3) > td > p > span.locality",
        )
        building = building[0].text if building else ""

        # サイトURLを取得
        home_page = driver.find_elements(By.CSS_SELECTOR, "#sv-site > li > a")
        if home_page:
            ssl, shop_url = get_shop_url_and_ssl(
                home_page[0].get_attribute("href"), driver
            )
        else:
            shop_url, ssl = "", ""

        # DataFrameに情報を格納
        df = pd.DataFrame(
            {
                "店舗名": [name],
                "電話番号": [phone],
                "メールアドレス": [email],
                "都道府県": [prefecture],
                "市区町村": [city],
                "番地": [street],
                "建物名": [building],
                "URL": [shop_url],
                "SSL": [ssl],
            }
        )

        df = df.applymap(lambda x: x.replace("\xa0", " ") if isinstance(x, str) else x)
        return df

    except Exception as e:
        print(f"エラーが発生しました。：{url}/{e}")
        return None


def get_shop_url_and_ssl(url, driver):
    """ショップのURLとSSL（https）かどうかを取得"""
    time.sleep(3)
    driver.get(url)
    shop_url = driver.current_url
    ssl = "TRUE" if shop_url.startswith("https") else "FALSE"
    return ssl, shop_url


def collect_info(base_url, max_count, driver):
    """指定されたURLから最大max_countの店舗情報を収集"""
    count = 0
    data = pd.DataFrame(
        {
            "店舗名": [],
            "電話番号": [],
            "メールアドレス": [],
            "都道府県": [],
            "市区町村": [],
            "番地": [],
            "建物名": [],
            "URL": [],
            "SSL": [],
        }
    )
    for url in generate_url(base_url, driver):
        driver = set_user_agent(driver)
        if count >= max_count:
            break
        new_data = get_infomation(url, driver)
        if new_data is not None:
            data = pd.concat([data, new_data], ignore_index=True)
            print(f"保存完了({count+1}/{max_count})")
            count += 1
        time.sleep(3)
    return data


if __name__ == "__main__":
    url = "https://r.gnavi.co.jp/area/jp/rs/?point=SAVE"
    options = webdriver.ChromeOptions()
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.1"
    )
    service = Service(r".\chromedriver-win64\chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    try:
        # 店舗情報を収集してCSVファイルに保存
        data = collect_info(url, 50, driver)
        data.to_csv("1-2.csv", index=True, encoding="cp932")
        print(f"csvファイルに保存しました")
    finally:
        driver.quit()
