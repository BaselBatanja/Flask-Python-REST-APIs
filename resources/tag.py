from flask.views import MethodView
from flask_smorest import abort, Blueprint

from schemas import TagSchema, TagAndItemSchema
from models import StoreModel, TagModel, ItemModel
from db import db
from sqlalchemy.exc import SQLAlchemyError

blp = Blueprint("tags", __name__, description="Operations on tags")


@blp.route("/store/<string:store_id>/tag")
class TagsInStore(MethodView):
    @blp.response(200, TagSchema(many=True))
    def get(self, store_id):
        store = StoreModel.query.get_or_404(store_id)
        return store.tags.all()

    @blp.arguments(TagSchema)
    @blp.response(201, TagSchema)
    def post(self, tag_data, store_id):
        tag = TagModel(**tag_data, store_id=store_id)

        try:
            db.session.add(tag)
            db.session.commit()
        except SQLAlchemyError as e:
            abort(500, message=str(e))

        return tag


@blp.route("/item/<string:item_id>/tag/<string:tag_id>")
class LinkTagsToItem(MethodView):
    @blp.response(201, TagSchema)
    def post(self, item_id, tag_id):
        item = ItemModel.query.get_or_404(item_id)
        tag = TagModel.query.get_or_404(tag_id)

        if item.store_id != tag.store_id:
            abort(400, message="Cannot link item with tag from different stores")

        item.tags.append(tag)

        try:
            db.session.add(item)
            db.session.commit()
        except SQLAlchemyError:
            abort(500, "An error occurred")

        return tag

    @blp.response(200, TagAndItemSchema)
    def delete(self, item_id, tag_id):
        item = ItemModel.query.get_or_404(item_id)
        tag = TagModel.query.get_or_404(tag_id)

        if item.store_id != tag.store_id:
            abort(400, message="Cannot link an item with a tag from different stores")

        item.tags.remove(tag)

        try:
            db.session.add(item)
            db.session.commit()
        except SQLAlchemyError:
            abort(500, message="An error occurred")

        return {"message": "Link removed", "item": item, "tag": tag}


@blp.route("/tag/<string:tag_id>")
class Tag(MethodView):
    @blp.response(200, TagSchema)
    def get(self, tag_id):
        tag = TagModel.query.get_or_404(tag_id)
        return tag

    @blp.response(202, description="Tag Deleted", example={"message": "Tag Deleted."})
    @blp.alt_response(404, description="Tag not exist")
    @blp.alt_response(400, description="Tag is assoicted to some items")
    def delete(self, tag_id):
        tag = TagModel.query.get_or_404(tag_id)

        if len(tag.items):
            abort(400, message="Tag is used from some items")

        try:
            db.session.delete(tag)
            db.session.commit()
        except SQLAlchemyError:
            abort(500, message="An error occurred")

        return {"message": "Tag deleted"}
