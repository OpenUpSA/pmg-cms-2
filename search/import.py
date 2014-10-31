from search import Search
import time

if (__name__ == "__main__"):
	start_time = time.time()
	search = Search()
	# search.drop("committee")
	search.import_data("committee-meeting")
	# search.import_content("committee")
	print("--- %d seconds ---" % (time.time() - start_time))