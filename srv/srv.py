from flask import redirect, Flask, request
from model import Analyser, DataProcessor 
import shutil


app = Flask(__name__)

TGT_FILEPATH = "/projects_core/sleeps/"

@app.route("/upload", methods=["POST", "GET"])
def upload():
	if request.method == "POST":
		file = request.files["file_inpute"]
		file.save(TGT_FILEPATH + file.filename)
		# shutil.copy(filepath, TGT_FILEPATH)
		return redirect("https://sleep.projectswhynot.site/time_page.html", code=302)
	else:
		# TODO: run processing and prediction
				
		return redirect("https://sleep.projectswhynot.site/results", code=302)

