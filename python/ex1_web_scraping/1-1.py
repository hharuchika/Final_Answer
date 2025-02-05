import requests
from bs4 import BeautifulSoup
import random
import time
import re
import pandas as pd


def generate_shop_url(url: str, user_agent: dict):
    """
    店舗情報を取得
    """
    page = 1
    header = {"user-agent": random.choice(user_agent)}

    while True:
        url += f"{url}&p={page}"
        res = requests.get(url, headers=header)
        print(f"取得中：{url}")
        time.sleep(3)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        link_all = soup.find_all("a", class_="style_titleLink__oiHVJ")

        if not link_all:
            print("店舗情報が載ったリンクを取得できませんでした。")
            break

        for link in link_all:
            yield link.get("href")
        page += 1


def check_ssl_certificate(url):
    try:
        response = requests.get(url, verify=True)
        return "TRUE"
    except requests.exceptions.SSLError:
        return "FALSE"


def get_shop_info(url: str, user_agent: list) -> list:
    """店舗情報を取得する"""
    header = {"user-agent": random.choice(user_agent)}
    try:
        res = requests.get(url, headers=header)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        info_table = soup.find(id="info-table")

        if not info_table:
            return None

        # 店舗名を取得
        name = (
            info_table.find(id="info-name").get_text(strip=True)
            if info_table.find(id="info-name")
            else ""
        )

        # emailを取得
        email = ""

        # 電話番号を取得
        phone_tag = info_table.select_one(
            "#info-phone > td > ul > li:nth-of-type(1) > span.number"
        )
        phone = phone_tag.get_text(strip="True") if phone_tag else ""

        # 住所を取得
        address_tag = info_table.select_one(
            "#info-table > table > tbody > tr:nth-of-type(3) > td > p > span.region"
        )
        address_full = address_tag.get_text(strip=True) if address_tag else ""

        # 住所を分割
        m = re.match(r"([^\s]+[都道府県])([^\s]+[市区町村])(.+)", address_full)
        prefecture, city, street = m.groups() if m else ("", "", "")

        building_tag = info_table.select_one(
            "#info-table > table > tbody > tr:nth-of-type(3) > td > p > span.locality"
        )
        building = building_tag.get_text(strip=True) if building_tag else ""

        # ssl証明
        shop_url_tag = soup.select_one("#sv-site > li > a")
        if shop_url_tag:
            shop_url = shop_url_tag.get("href")
            ssl = check_ssl_certificate(shop_url)
        else:
            shop_url, ssl = "", ""

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
        df = df.applymap(lambda x: x.replace("\xa0", "") if isinstance(x, str) else x)
        return df
    except Exception as e:
        print(f"エラーが発生しました（{url}）: {e}")
        return None


def save_to_csv(file_name, max_count, base_url, user_agent):
    """店舗情報をCSVファイルに出力"""
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

    count = 0
    for url in generate_shop_url(base_url, user_agent):
        if count >= max_count:
            break
        new_data = get_shop_info(url, user_agent)

        if new_data is not None:
            data = pd.concat([data, new_data], ignore_index=True)
            print(f"データを追加完了 ({count + 1}/{max_count})")
            count += 1
        time.sleep(3)
    data.to_csv(file_name, index=True, encoding="cp932")


if __name__ == "__main__":
    base_url = "https://r.gnavi.co.jp/area/jp/rs/?point=SAVE"
    user_agent = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.",
    ]
    save_to_csv("1-1.csv", 50, base_url, user_agent)
