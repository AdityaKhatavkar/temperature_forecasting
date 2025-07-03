## flask --> app2.py
#

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from dbmodles.weather import db
from routs.main_routs import main

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
app.register_blueprint(main)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
