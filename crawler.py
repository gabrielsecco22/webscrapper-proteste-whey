import json
import os

import pandas as pd
from bs4 import BeautifulSoup
import requests

def weight_to_grams(weight):
    """Converts a weight string to grams"""
    dw = weight.replace(',', '.')
    if weight.endswith('g'):
        return float(dw[:-1])
    elif weight.endswith('kg'):
        return float(dw[:-2]) * 1000
    else:
        raise ValueError(f"Invalid weight: {weight}")

def read_page(url):
    """Reads a page and returns the content"""
    page = requests.get(url)
    return page.content

def parse_page(content):
    """Parses the content of a page and returns a list of products"""
    soup = BeautifulSoup(content, 'html.parser')
    # products = soup.find_all('tbody', class_='gs-list-body')
    products = soup.find_all('tr', class_='gs-list-row item')
    return products

def get_products_info(products):
    """Returns a list of dictionaries with the product information"""
    products_info = []
    for product in products:
        product_info = {}
        product_info['name'] = product.find('h3', class_="nome-produto").text
        product_details = [x.text for x in list(product.find('div', class_="descricao").children) if x.text != '\n']
        for pds in product_details:
            try:
                if pds.startswith('Peso:'):
                    product_info['weight_grams'] = weight_to_grams(pds.split(':')[1].strip())
                elif pds.startswith('Preço Médio:'):
                    product_info['price'] = float(pds.split('$')[1].strip().replace(',', '.'))
                elif pds.startswith('Porção:'):
                    product_info['serving_grams'] = weight_to_grams(pds.split(':')[1].strip())
                elif pds.startswith('\nTipo de whey (proteína):'):
                    product_info['whey_type'] = pds.split(':')[1].split(' ')[2].strip()
                    product_info['ingredients'] = pds.split(':')[2].strip().replace('\n', '').split(" Resultado -")[0].split(',')
                    lines = pds.split('\n')
                    for line in lines:
                        if line.startswith('Resultado - teste de proteína:'):
                            product_info['protein_label_grams'] = weight_to_grams(line.split('Rótulo: ')[1].split('x')[0].strip())
                            product_info['protein_measured_grams'] = weight_to_grams(line.split('Teste')[1].split(' ')[1].strip())
                        elif line.startswith('Resultado - teste de carboidrato:'):
                            product_info['carbo_label_grams'] = weight_to_grams(line.split('Rótulo: ')[1].split('x')[0].strip())
                            product_info['carbo_measured_grams'] = weight_to_grams(line.split('Teste')[1].split(' ')[1].strip())
            except Exception as e:
                print(f"Error parsing product: {product_info['name']}")
                print(e)

        products_info.append(product_info)
    return products_info

def main():
    # if whey.pkl exists, read it
    # else, read all pages and save to whey.pkl
    if os.path.exists('whey.pkl'):
        df = pd.read_pickle('whey.pkl')
    else:
        # read all pages
        p = []
        for i in range(1, 9):
            site_url = f"https://www.proteste.org.br/saude-e-bem-estar/bem-estar/teste/whey-protein?page={i}&gsorder=&gsfilter="
            print(f"Reading page {i}...")
            content = read_page(site_url)
            products = parse_page(content)
            products_info = get_products_info(products)
            p.extend(products_info)
        print(json.dumps(p, indent=4))
        df = pd.DataFrame(p)
        df.to_pickle('whey.pkl')
    df['protein_label_percentage'] = df['protein_label_grams'] / df['serving_grams'] * 100
    df['protein_measured_percentage'] = df['protein_measured_grams'] / df['serving_grams'] * 100
    df['carbo_label_percentage'] = df['carbo_label_grams'] / df['serving_grams'] * 100
    df['carbo_measured_percentage'] = df['carbo_measured_grams'] / df['serving_grams'] * 100
    df['servings_total'] = df['weight_grams'] / df['serving_grams']
    df['price_per_protein_gram'] = df['price'] / (df['protein_measured_grams'] * df['servings_total'])
    print(df.sort_values(by='price_per_protein_gram').head(10))


if __name__ == "__main__":
    main()