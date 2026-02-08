-- 销售分析示例数据库
-- Sales analytics sample database

-- 客户表
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150),
    city VARCHAR(80),
    province VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 产品表
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(80) NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    stock_qty INTEGER DEFAULT 0
);

-- 订单表
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    total_amount NUMERIC(12,2)
);

-- 订单明细表
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    subtotal NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- ========== 示例数据 ==========

INSERT INTO customers (name, email, city, province) VALUES
('张三', 'zhangsan@example.com', '北京', '北京'),
('李四', 'lisi@example.com', '上海', '上海'),
('王五', 'wangwu@example.com', '深圳', '广东'),
('赵六', 'zhaoliu@example.com', '杭州', '浙江'),
('孙七', 'sunqi@example.com', '成都', '四川'),
('周八', 'zhouba@example.com', '广州', '广东'),
('吴九', 'wujiu@example.com', '南京', '江苏'),
('郑十', 'zhengshi@example.com', '武汉', '湖北');

INSERT INTO products (name, category, unit_price, stock_qty) VALUES
('笔记本电脑 Pro', '电子产品', 8999.00, 150),
('无线鼠标', '电子产品', 199.00, 500),
('机械键盘', '电子产品', 599.00, 300),
('显示器 27寸', '电子产品', 2499.00, 80),
('办公椅', '办公家具', 1299.00, 120),
('升降桌', '办公家具', 2999.00, 60),
('降噪耳机', '电子产品', 1599.00, 200),
('USB-C 扩展坞', '电子产品', 399.00, 400),
('文件柜', '办公家具', 899.00, 90),
('台灯', '办公家具', 299.00, 250);

-- 生成 2024-2025 年的订单数据
DO $$
DECLARE
    i INTEGER;
    cust_id INTEGER;
    ord_id INTEGER;
    ord_date DATE;
    prod_id INTEGER;
    qty INTEGER;
    price NUMERIC;
    total NUMERIC;
BEGIN
    FOR i IN 1..200 LOOP
        cust_id := (random() * 7 + 1)::INTEGER;
        ord_date := '2024-01-01'::DATE + (random() * 730)::INTEGER;

        INSERT INTO orders (customer_id, order_date, status, total_amount)
        VALUES (cust_id, ord_date,
                CASE WHEN random() > 0.1 THEN 'completed' ELSE 'cancelled' END,
                0)
        RETURNING id INTO ord_id;

        total := 0;
        FOR j IN 1..(random() * 3 + 1)::INTEGER LOOP
            prod_id := (random() * 9 + 1)::INTEGER;
            qty := (random() * 4 + 1)::INTEGER;

            SELECT unit_price INTO price FROM products WHERE id = prod_id;

            INSERT INTO order_items (order_id, product_id, quantity, unit_price)
            VALUES (ord_id, prod_id, qty, price);

            total := total + qty * price;
        END LOOP;

        UPDATE orders SET total_amount = total WHERE id = ord_id;
    END LOOP;
END $$;
