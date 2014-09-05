from backend_drupal.app import app

if __name__ == "__main__":
    # run Flask dev-server
    app.run(port=5001)