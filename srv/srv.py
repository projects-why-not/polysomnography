from flask import redirect, Flask, request
from model import Analyser, DataProcessor 
import shutil
import os


app = Flask(__name__)

TGT_FILEPATH = "/projects_core/sleeps/"
CUR_STUDY = None

@app.route("/upload", methods=["POST", "GET"])
def upload():
	if request.method == "POST":
		file = request.files["file_inpute"]
		file.save(TGT_FILEPATH + file.filename)
		# shutil.copy(filepath, TGT_FILEPATH)
		os.system(f'unzip {TGT_FILEPATH + file.filename} -d {TGT_FILEPATH + file.filename.split(".zip")[0]}')
		os.system(f"rm {TGT_FILEPATH + file.filename}")
		global CUR_STUDY
		CUR_STUDY = TGT_FILEPATH + file.filename.split(".zip")[0]
		return redirect("https://sleep.projectswhynot.site/time_page.html", code=302)
	else:
		# global CUR_STUDY
		# TODO: run processing and prediction
		analyser = Analyser(CUR_STUDY, "model/pretrained_model/model")

		return redirect("https://sleep.projectswhynot.site/results", code=302)

