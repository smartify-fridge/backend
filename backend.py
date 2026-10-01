from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

from models.shelf import Shelf

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/shelves", methods=["GET"])
def shelves():
    shelves = Shelf.query.all()
    return {"shelves": [shelf.name for shelf in shelves]}

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
