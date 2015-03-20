Parliamentary Monitoring Group website (pmg-cms-2)
==================================================

Parliamentary monitoring application for use by the Parliamentary Monitoring Group in Cape Town, South Africa. 
See: https://www.pmg.org.za.

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
  * Admin interface (Flask-Admin, integration with Mandrill for email notifications)
    * https://api.pmg.org.za/admin
  * API (Flask)
    * https://api.pmg.org.za

## Making use of the API

All of the data that is displayed through the frontend website, is served
through an API (https://api.pmg.org.za), which is freely accessible.  However,
please note that access to some content on the frontend website is restricted,
and the same restrictions apply for the API. 

If you are a registered user, and you wish to have access to restricted content through the API, then please follow 
these steps:

1. Login to the website at https://pmg.org.za using your browser.
2. Visit https://api.pmg.org.za/user/ and get the authentication token from the JSON response.
3. Include the authentication token in subsequent requests to tha API in a header named `Authentication-Token`.
4. You can check if you are correctly authenticated by doing a GET against https://api.pmg.org.za/user/

        {
            "current_user": {
                "organisation_id": null,
                "confirmed": true,
                "name": "your name",
                "subscribe_daily_schedule": true,
                "has_expired": false,
                "email": "email@example.com",
                "committee_alerts": {},
                "active": true,
                "id": 999,
                "expiry": null
            }
        }

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


### Database migration

We use alembic for applying changes to the data model. To setup a migration script:

    alembic -c 'config/development/alembic.ini' revision --autogenerate -m "<revision description>"
    
Then to run the script on your local machine: 

    alembic -c 'config/development/alembic.ini' upgrade head
    
but first, ensure that the `sqlalchemy.url` parameter is pointing at the right place.

To run migration scripts on the live database, copy the `alembic.ini` into the production config directory, update the
`sqlalchemy.url` parameter, and 

    alembic -c 'config/production/alembic.ini' upgrade head
    
Never add the production configuration to git, as it contains sensitive database credentials.
