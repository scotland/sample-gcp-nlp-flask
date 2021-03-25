from datetime import datetime
import logging
import os

from flask import Flask, redirect, render_template, request

from google.cloud import datastore
from google.cloud import language_v1 as language

import requests
import xml.etree.ElementTree as ET




app = Flask(__name__)


@app.route("/")
def homepage():
    # Create a Cloud Datastore client.
    datastore_client = datastore.Client()

    # # Use the Cloud Datastore client to fetch information from Datastore
    # Query looks for all documents of the 'Sentences' kind, which is how we
    # store them in upload_text()
    query = datastore_client.query(kind="Sentences")
    text_entities = list(query.fetch())

    # # Return a Jinja2 HTML template and pass in text_entities as a parameter.
    return render_template("homepage.html", text_entities=text_entities)


@app.route("/upload", methods=["GET", "POST"])
def upload_text():
    url = request.form["text"]

    resp = requests.get(url)
    tree = ET.ElementTree(ET.fromstring(resp.content))
    root = tree.getroot()
    news_items = []
    for item in root.findall('./'):
        for child in item:
            if child.tag == 'richText' and child.text:
                news_items.append(child.text)

    # Create a Cloud Datastore client.
    datastore_client = datastore.Client()

    # The kind for the new entity. This is so all 'Sentences' can be queried.
    kind = "Sentences"

    # Create the Cloud Datastore key for the new entity.
    

    for i,item in enumerate(news_items):
        categories = gcp_classify_text(item)
        key = datastore_client.key(kind, 'sample_task'+str(i))
        entity = datastore.Entity(key, exclude_from_indexes=('text', 'categories'))
        entity["text"] = item
        cats = []
        for category in categories:
            cats.append(f"category  : {category.name} with confidence: {category.confidence:.0%}")
        entity["categories"] = ','.join(cats)

        # Save the new entity to Datastore.
        datastore_client.put(entity)


    # Redirect to the home page.
    return redirect("/")


@app.errorhandler(500)
def server_error(e):
    logging.exception("An error occurred during a request.")
    return (
        """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(
            e
        ),
        500,
    )

def gcp_classify_text(text):
    client = language.LanguageServiceClient()
    document = language.Document(content=text, type_=language.Document.Type.PLAIN_TEXT)

    response = client.classify_text(document=document)

    return response.categories


if __name__ == "__main__":
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host="127.0.0.1", port=8080, debug=True)
