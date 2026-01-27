from flask import Blueprint

prakriti_bp = Blueprint(
    "prakriti",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/prakriti"
)

from . import routes
