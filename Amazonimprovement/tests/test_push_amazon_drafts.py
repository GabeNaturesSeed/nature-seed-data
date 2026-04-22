import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_check_completeness_ready():
    from push_amazon_drafts import check_completeness
    row = {
        'product_name': 'Kentucky Bluegrass Seed',
        'parent_sku': 'NS-KBG-5LB',
        'bullet_1': 'Fast germination',
        'bullet_2': 'Dense coverage',
        'bullet_3': 'Drought tolerant',
        'bullet_4': 'Fine texture',
        'bullet_5': 'Persistent stand',
        'description_plain': 'Premium Kentucky Bluegrass for home lawns and athletic fields.',
        'image_1': 'https://example.com/img1.jpg',
        'price': '29.99',
    }
    result = check_completeness(row)
    assert result['ready'] is True
    assert result['missing'] == []

def test_check_completeness_missing_bullets():
    from push_amazon_drafts import check_completeness
    row = {
        'product_name': 'Kentucky Bluegrass Seed',
        'parent_sku': 'NS-KBG-5LB',
        'bullet_1': 'Fast germination',
        'bullet_2': 'Dense coverage',
        'bullet_3': '',
        'bullet_4': '',
        'bullet_5': '',
        'description_plain': 'Premium Kentucky Bluegrass seed for home lawns and athletic fields across the US.',
        'image_1': 'https://example.com/img1.jpg',
        'price': '29.99',
    }
    result = check_completeness(row)
    assert result['ready'] is False
    assert 'bullets' in result['missing']

def test_check_completeness_missing_image():
    from push_amazon_drafts import check_completeness
    row = {
        'product_name': 'Kentucky Bluegrass Seed',
        'parent_sku': 'NS-KBG-5LB',
        'bullet_1': 'b1', 'bullet_2': 'b2', 'bullet_3': 'b3', 'bullet_4': 'b4', 'bullet_5': 'b5',
        'description_plain': 'Premium Kentucky Bluegrass seed for home lawns and athletic fields across the US.',
        'image_1': '',
        'price': '29.99',
    }
    result = check_completeness(row)
    assert result['ready'] is False
    assert 'images' in result['missing']

def test_check_completeness_missing_price():
    from push_amazon_drafts import check_completeness
    row = {
        'product_name': 'Kentucky Bluegrass Seed',
        'parent_sku': 'NS-KBG-5LB',
        'bullet_1': 'b1', 'bullet_2': 'b2', 'bullet_3': 'b3', 'bullet_4': 'b4', 'bullet_5': 'b5',
        'description_plain': 'Premium Kentucky Bluegrass seed for home lawns and athletic fields across the US.',
        'image_1': 'https://example.com/img1.jpg',
        'price': '0',
    }
    result = check_completeness(row)
    assert result['ready'] is False
    assert 'price' in result['missing']

def test_check_completeness_missing_description():
    from push_amazon_drafts import check_completeness
    row = {
        'product_name': 'Kentucky Bluegrass Seed',
        'parent_sku': 'NS-KBG-5LB',
        'bullet_1': 'b1', 'bullet_2': 'b2', 'bullet_3': 'b3', 'bullet_4': 'b4', 'bullet_5': 'b5',
        'description_plain': 'Too short.',
        'image_1': 'https://example.com/img1.jpg',
        'price': '29.99',
    }
    result = check_completeness(row)
    assert result['ready'] is False
    assert 'description' in result['missing']
