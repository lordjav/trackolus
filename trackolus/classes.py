#create class "product"
class prototype_product:
    def __init__(
                self,
                id, 
                SKU,
                product_name, 
                buy_price, 
                sell_price, 
                author, 
                addition_date, 
                image_route,                
                ):
        self.id = id
        self.SKU = SKU
        self.product_name = product_name
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.author = author
        self.addition_date = addition_date
        self.image_route = image_route
        self.warehouses = {}
        self.other_props = {}

    def add_warehouse_stock(self, warehouse_id, stock):
        self.warehouses[warehouse_id] = stock

    @property
    def total_stock(self):
        return sum(self.warehouses.values())
    
    def get_stock_by_warehouse(self, warehouse_id):
        return self.warehouses.get(warehouse_id, 0)
    
    def update_stock(self, warehouse_id, quantity):
        if warehouse_id in self.warehouses:
            self.warehouses[warehouse_id] += quantity
        else:
            self.warehouses[warehouse_id] = quantity

    def remove_stock(self, warehouse_id, quantity):
        if warehouse_id in self.warehouses:
            if self.warehouses[warehouse_id] >= quantity:
                self.warehouses[warehouse_id] -= quantity
            else:
                raise ValueError(f'Insufficient stock in warehouse {warehouse_id}.')
        else:
            raise ValueError(f'Warehouse "{warehouse_id}" not found.')

    def to_dict(self):
        return {
            'id': self.id,
            'SKU': self.SKU,
            'product_name': self.product_name,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'author': self.author,
            'addition_date': self.addition_date,
            'image_route': self.image_route,
            'warehouses': self.warehouses,
            'other_props': self.other_props,
        }

#Create class "customer"
class customer:
    def __init__(self, name, customer_id, customer_phone, customer_email):
        self.name = name
        self.id = customer_id
        self.phone = customer_phone
        self.email = customer_email


#Create class "order_object"
class prototype_order:
    def __init__(
            self, 
            order_number, 
            order_type, 
            order_date, 
            order_author, 
            order_counterpart
            ):
        self.order_number = order_number
        self.order_type = order_type
        self.order_date = order_date
        self.order_products = []
        self.order_author = order_author
        self.order_counterpart = order_counterpart
        self.order_props = {}

    def add_products(self, product_object):
        self.order_products.append(product_object)

    def add_prop(self, key, value):
        self.order_props[key] = value
