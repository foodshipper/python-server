import requests
from flask_restful import Resource, abort, reqparse

from ean.database import db

parser = reqparse.RequestParser()
parser.add_argument('name')
parser.add_argument('type', required=True)


class Product(Resource):
    @staticmethod
    def get(ean):
        with db:
            with db.cursor() as cursor:
                cursor.execute("SELECT name, type FROM products"
                               " WHERE ean=%s", (ean,))
                product = cursor.fetchone()
                if product is not None:
                    return {
                        "ean": ean,
                        "name": product[0],
                        "type": product[1]
                    }
                else:
                    result = ProductData.request_product(ean)
                    if result is not None:
                        Product.add_product(result['ean'], result['name'], result['type'])
                        return result

                    abort(404, message="Product with EAN {} does not exist.".format(ean))

    def put(self, ean):
        try:
            args = parser.parse_args()
            args['type'] = int(args['type'])
        except Exception:
            return abort(400, message="Invalid arguments")

        if args['name'] is None or len(args['name']) == 0:
            args['name'] = "Unknown"

        with db:
            with db.cursor() as cursor:
                cursor.execute("SELECT id FROM product_types WHERE id=%s", [args['type']])
                if cursor.fetchone() is None:
                    abort(400, message="Invalid arguments, product type does not exist.")

                cursor.execute("SELECT name, type FROM products WHERE ean=%s", [ean,])
                if cursor.fetchone() is None:
                    self.add_product(ean, args['name'], args['type'])
                    return None, 201
                else:
                    cursor.execute("UPDATE products SET name=%s, type=%s WHERE ean=%s",
                                   (args['name'], args['type'], ean))
                    db.commit()
                    return None, 200

    @staticmethod
    def add_product(ean, name, product_type):
        with db:
            with db.cursor() as cursor:
                cursor.execute("INSERT INTO products (ean, name, type) VALUES (%s, %s, %s)", (ean, name, product_type))


class ProductData:
    @staticmethod
    def request_product(gtin):
        req = requests.get(
            'http://pod.opendatasoft.com/api/records/1.0/search/?dataset=pod_gtin&rows=1&refine.gtin_cd={}'.format(
                gtin))
        if req.status_code == requests.codes.ok:
            product = req.json()
            if product['nhits'] == 0:
                return None
            if 'gtin_nm' not in product['records'][0]['fields']:
                return None
            return {
                "ean": gtin,
                "name": product['records'][0]['fields']['gtin_nm'],
                "type": 1 # Is always undefined
                # TODO: Add Product Type recognition from recipe API
            }
        else:
            return None


class ProductTypes(Resource):
    def get(self):
        with db:
            with db.cursor() as cursor:
                cursor.execute("SELECT id, name, image FROM product_types")
                result = []
                for row in cursor.fetchall():
                    result.append({'id': row[0], 'name': row[1], 'image': row[2]})
                return result
