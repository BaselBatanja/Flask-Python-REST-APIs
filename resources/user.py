from flask.views import MethodView
from flask_smorest import Blueprint, abort
from passlib.hash import pbkdf2_sha256

from db import db
from models import UserModel
from schemas import UserSchema

from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    jwt_required,
    create_refresh_token,
    get_jwt_identity,
)
from blocklist import BLOCKLIST

blp = Blueprint("Users", "users", description="Operations on users")


@blp.route("/register")
class UserRegister(MethodView):
    @blp.arguments(UserSchema)
    def post(self, request_data):
        if UserModel.query.filter(
            UserModel.username == request_data["username"]
        ).first():
            abort(409, message="A user with this username already exists.")

        user = UserModel(
            username=request_data["username"],
            password=pbkdf2_sha256.hash(request_data["password"]),
        )

        try:
            db.session.add(user)
            db.session.commit()
        except SQLAlchemyError:
            abort(500, message="An error occurred")

        return {"message": "Created successfully"}, 201


@blp.route("/login")
class Login(MethodView):
    @blp.arguments(UserSchema)
    def post(self, request_data):
        user = UserModel.query.filter(
            UserModel.username == request_data["username"]
        ).first()

        if user and pbkdf2_sha256.verify(request_data["password"], user.password):
            access_token = create_access_token(identity=str(user.id), fresh=True)
            refresh_token = create_refresh_token(identity=str(user.id))
            return {"access_token": access_token, "refresh_token": refresh_token}

        abort(401, message="Invalid credentials.")


@blp.route("/refresh")
class TokenRefresh(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        # Make it clear that when to add the refresh token to the blocklist will depend on the app design
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return {"access_token": new_token}, 200


@blp.route("/user/<int:user_id>")
class User(MethodView):
    @blp.response(200, UserSchema)
    def get(self, user_id):
        user = UserModel.query.get_or_404(user_id)
        return user

    def delete(self, user_id):
        user = UserModel.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted"}


@blp.route("/logout")
class UserLogout(MethodView):
    @jwt_required()
    def post(self):
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return {"message": "Successfully logged out"}, 200
