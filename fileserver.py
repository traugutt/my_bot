from flask import Flask, render_template
from flask import Flask, render_template, send_file


app = Flask(__name__, static_url_path="", static_folder="bot_audio")


@app.route("/<path:filename>", methods=["GET", "POST"])
def serve(filename):
    return send_file(filename)


