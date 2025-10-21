class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")
        if not cart:
            cart = self.session["cart"] = {}
        self.cart = cart

    def add(self, product, quantity=1):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {"quantity": 0, "price": str(product.price)}

        # Verificar stock antes de añadir
        if self.cart[product_id]["quantity"] + quantity <= product.stock:
            self.cart[product_id]["quantity"] += quantity
        else:
            self.cart[product_id]["quantity"] = product.stock 

        self.save()


    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        self.session["cart"] = {}
        self.session.modified = True

    def save(self):
        self.session["cart"] = self.cart
        self.session.modified = True

    def __iter__(self):
        from .models import Product
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        for product in products:
            cart_item = self.cart[str(product.id)]
            cart_item["product"] = product
            cart_item["total_price"] = float(cart_item["price"]) * cart_item["quantity"]
            yield cart_item

    def total(self):
        return sum(float(item["price"]) * item["quantity"] for item in self.cart.values())
