#models and database function

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# -------- MODELS --------------

class User(db.Model):
    """
    user info
    """

    __tablename__ = "users"

    user_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    profile_pic_url = db.Column(db.String(150), nullable=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.city_id'), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)

    city = db.relationship("City", backref=db.backref("users"))

    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<User user_id=%s email=%s>" % (self.user_id,
                                               self.email)


class Trail(db.Model):
    """
    trail info
    """

    __tablename__ = "trails"

    trail_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.city_id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(150), nullable=False)
    distance = db.Column(db.Numeric, nullable=False)
    trail_type = db.Column(db.String(100), nullable=True)
    latitude = db.Column(db.Numeric, nullable=False)
    longitude = db.Column(db.Numeric, nullable=False)
    image_url = db.Column(db.String(200), nullable=False)

    city = db.relationship("City", backref=db.backref("trails"))
    users = db.relationship("User", secondary="visits", backref="trails")

    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<Trail trail=%s name=%s>" % (self.trail_id,
                                              self.name)


class Visit(db.Model):
    """
    user's visits
    """

    __tablename__ = "visits"

    visit_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    visit_date = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    trail_id = db.Column(db.Integer, db.ForeignKey('trails.trail_id'), nullable=False)

    user = db.relationship("User", backref=db.backref("visits"))
    trail = db.relationship("Trail", backref=db.backref("visits"))

    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<Visit visit_id=%s trail=%s>" % (self.visit_id,
                                                  self.trail_id)


class City(db.Model):
    """
    users' cities
    """

    __tablename__ = "cities"

    city_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<City city_id=%s name=%s>" % (self.city_id,
                                              self.name)


class Connection(db.Model):
    """
    Connection between two users
    """

    __tablename__ = "connections"

    connection_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    user_b_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    status = db.Column(db.String(100), nullable=False)

    #When both columns have a relationship with the same table, need to specify how
    #to handle multiple join paths in the square brackets of foreign_keys per below
    user_a = db.relationship("User", foreign_keys=[user_a_id], backref=db.backref("sent_connections"))
    user_b = db.relationship("User", foreign_keys=[user_b_id], backref=db.backref("received_connections"))

    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<Connection connection_id=%s user_a_id=%s user_b_id=%s status=%s>" % (self.connection_id,
                                                                                      self.user_a_id,
                                                                                      self.user_b_id,
    
                                                                                      self.status)
# ------- connect to database -------
def connect_to_db(app, db_uri=None):
    """
    connect app to database
    """

    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri or 'postgresql:///hikesf'
    app.config['SQLALCHEMY_ECHO'] = True
    db.app = app
    db.init_app(app)

