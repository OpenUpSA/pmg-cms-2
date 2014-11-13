from datetime import datetime
import requests
from lxml import html
from flask import Flask
import re
import sys
from cssselect import GenericTranslator
import argparse
import sys, os 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backend.app import app, db
from backend import models
from backend.models import *
import parsers
from sqlalchemy import types

app = Flask(__name__)

class Scraper:

	dows = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

	def test(self):
		print "Test!"
		return

	def _save_schedule(self, items):
		for key in items:
			print items[key]
			schedule = Schedule()
			schedule.description = items[key]["description"]
			schedule.meeting_date = key
			schedule.meeting_time = items[key]["time"]
			# for house in items[key]["house"]:
			# 	print house
			# 	schedule.houses.append(house)
			if (schedule.description):
				db.session.add(schedule)
		db.session.commit()

	def schedule(self):
		url = "http://www.pmg.org.za/schedule"
		url = "http://www.pmg.org.za/daily-schedule/" + datetime.now().strftime('%Y/%m/%d') + "/daily-schedule"
		print "Fetching ", url
		page = requests.get(url)
		tree = html.fromstring(page.text)
		# content = tree.xpath('//*[@id="content"]/div[3]/div[1]/div/div/div[3]/p[3]/text()')
		xpath = GenericTranslator().css_to_xpath('#content > div.node > div.content')
		for p in tree.xpath(xpath + "/p"):
			content = p.text_content().encode('utf8', 'replace').strip()
			if content.split(', ', 1)[0] in self.dows:
				break;
		in_date = False
		result = {}
		
		for part in content.split("\n"):
			part = part.strip()
			if part:
				if part.split(', ', 1)[0] in self.dows:
					in_date = date_object = datetime.strptime(part, '%A, %d %B %Y')
					result[in_date] = {}
				else:
					result[in_date]["house"] = []
					if part.find("(National Assembly and National Council of Provinces)") > -1:
						result[in_date]["house"] = ["National Assembly", "NCOP"]
						part = re.sub("\(National Assembly and National Council of Provinces\),", "", part).strip()
					elif part.find("(National Assembly)") > -1:
						result[in_date]["house"] = ["National Assembly"]
						part = re.sub("\(National Assembly\),", "", part).strip()
					elif part.find("(National Council of Provinces)") > -1:
						result[in_date]["house"] = ["NCOP"]
						part = re.sub("\(National Council of Provinces\),", "", part).strip()
					time = re.search(r"[0-9][0-9]\:[0-9][0-9]", part)
					if time:
						result[in_date]["time"] = time.group()
						part = re.sub(r"\,\s[0-9][0-9]\:[0-9][0-9]", "", part)
					result[in_date]["description"] = re.sub(r"[^\w\s]", "", part)
		print result
		self._save_schedule(result)
		return

if (__name__ == "__main__"):
	parser = argparse.ArgumentParser(description='Scrapers for PMG')
	parser.add_argument('scraper')
	args = parser.parse_args()
	scraper = Scraper()
	method = getattr(scraper, args.scraper)
	if not method:
		raise Exception("Method %s not implemented" % args.scraper)
	method()