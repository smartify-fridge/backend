from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

from models.item import Item
from models.shelf import Shelf

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

# shelf routes

@app.route("/shelves", methods=["GET"])
def shelves():
    shelves = Shelf.query.all()
    return {"shelves": [{shelf.name: shelf.id} for shelf in shelves]}

@app.route("/shelf/<int:id>", methods=["GET", "POST"])
def shelf(id):
    if (request.method == "POST"):
        data = request.get_json()
        shelf = Shelf.query.get_or_404(id)
        shelf.name = data.get("name", shelf.name)
        shelf.description = data.get("description", shelf.description)
        db.session.commit()
        return {"message": "Shelf updated successfully."}, 200
    elif (request.method == "GET"):
        shelf = Shelf.query.get_or_404(id)
        return {"shelf": shelf.name, "description": shelf.description, "items": [item.name for item in shelf.items]}

@app.route("/shelf", methods=["POST"])
def create_shelf():
    data = request.get_json()
    new_shelf = Shelf(
        name=data["name"],
        description=data.get("description", ""),
    )
    db.session.add(new_shelf)
    db.session.commit()
    return {"message": "Shelf created successfully.", "shelf_id": new_shelf.id}, 201

@app.route("/shelf/<int:id>", methods=["DELETE"])
def delete_shelf(id):
    shelf = Shelf.query.get_or_404(id)
    db.session.delete(shelf)
    db.session.commit()
    return {"message": "Shelf deleted successfully."}, 200

# item routes

@app.route("/item/<int:id>", methods=["GET", "POST"])
def item(id):
    if (request.method == "POST"):
        data = request.get_json()
        item = Item.query.get_or_404(id)
        item.name = data.get("name", item.name)
        item.image = data.get("image", item.image)
        item.shelf_id = data.get("shelf_id", item.shelf_id)
        db.session.commit()
        return {"message": "Item updated successfully."}, 200
    elif (request.method == "GET"):
        item = Item.query.get_or_404(id)
        return {"item": item.name, "image": item.image, "shelf_id": item.shelf_id}

@app.route("/item", methods=["POST"])
def create_item():
    data = request.get_json()
    new_item = Item(
        name=data["name"],
        image=data.get("image", ""),
        shelf_id=data["shelf_id"]
    )
    db.session.add(new_item)
    db.session.commit()
    return {"message": "Item created successfully.", "item_id": new_item.id}, 201

@app.route("/item/<int:id>", methods=["DELETE"])
def delete_item(id):
    item = Item.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return {"message": "Item deleted successfully."}, 200
