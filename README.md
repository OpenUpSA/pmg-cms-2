Parliamentary Monitoring Group website (pmg-cms-2)
==================================================

Parliamentary monitoring application for use by the Parliamentary Monitoring Group in Cape Town, South Africa. 
When live, this will be hosted at http://www.pmg.org.za.

## What does this project do

Allow citizens and other interested parties to monitor what's going on in the South African parliament. With specific 
focus on tracking the progress of legislation as it moves through the various phases: from being introduced for the 
first time to finally being approved and signed into law.

The purpose of the project is to improve parliamentary oversight, make the parliamentary process more accessible
and improve transparency surrounding the activities of parliament.

## How it works

The project consists of the following major components:

  * User-facing website, including free and paid-for content (built using Flask, Jinja2 templates, Bootstrap and jQuery)
    * http://new.pmg.org.za
  * Database (PostgreSQL)
  * Search engine (Elastic Search)
  * Admin interface (Flask-Admin, integration with MailChimp)
    * http://api.pmg.org.za/admin
  * API (Flask)
    * http://api.pmg.org.za

## Contributing to the project

This project is open-source, and anyone is welcome to contribute. If you just want to make us aware of a bug / make
a feature request, then please add a new GitHub Issue (if a similar one does not already exist).

If you want to contribute to the code, please fork the repository, make your changes, and create a pull request.

### Local setup

Clone this repo, and setup a virtualenv:

    virtualenv --no-site-packages env
    source env/bin/activate

Install requirements:

    pip install -r requirements.txt

Add the following lines to your `.hosts` file:

    127.0.0.1 api.pmg.dev
    127.0.0.1 pmg.dev

Start the backend server:

    python runserver_backend.py

And start the frontend server:

    python runserver_frontend.py

You should now see them running at `http://api.pmg.dev:5001/` and `http://pmg.dev:5000/` respectively.


### Deploy instructions

Deployment is via fabric from the master branch on GitHub. You need to have an ssh key to access the server.

Now, deploy the latest code from this project's master branch on GitHub:::

    fab production deploy

To deploy a new instance (requires Ubuntu 14.04), use:

    fab production setup deploy

On production, certain private config variables are loaded as environment variables by running
a shell script `production-env.sh` from the project directory during startup. The script is of
the following form::

    export SQLALCHEMY_DATABASE_URI=XXX
    export FLASK_ENV=XXX
    export AWS_ACCESS_KEY_ID=XXX
    export AWS_SECRET_ACCESS_KEY=XXX
    export MAIL_PASSWORD=XXX
    export SECURITY_PASSWORD_SALT=XXX
