from frontend import app as app_frontend

if __name__ == "__main__":
    # run Flask dev-server
    app_frontend.run(port=5000, threaded=True)
