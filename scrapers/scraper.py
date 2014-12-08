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
from bs4 import BeautifulSoup
import csv
from urlparse import urljoin

app = Flask(__name__)

import logging
logger = logging.getLogger()

class Scraper:

	dows = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
	missing_committees = []

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
		url = "http://www.pmg.org.za/daily-schedule/" + datetime.datetime.now().strftime('%Y/%m/%d') + "/daily-schedule"
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
					in_date = date_object = datetime.datetime.strptime(part, '%A, %d %B %Y')
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

	def _save_tabledreport(self, title, committee_name, body):
		tabled_committee_report = Tabled_committee_report()
		committee = Organisation.query.filter_by(name=committee_name).first()
		if (committee):
			tabled_committee_report.title = title
			tabled_committee_report.body = body
			tabled_committee_report.committee.append(committee)
			db.session.add(tabled_committee_report)
		else:
			if committee_name not in self.missing_committees:
				self.missing_committees.append(committee_name)
		db.session.commit()

	def _report_exists(self, title, committee_name):
		committee = Organisation.query.filter_by(name=committee_name).first()
		if (committee):
			check = Tabled_committee_report.query.filter_by(title=title).first()
			if check:
				return True
		return False

	def tabledreports(self):

		# url = "http://pmg.org.za/tabled-committee-reports-2008-2013"
		# print "Fetching", url
		# page = requests.get(url)
		# txt = page.text
		f = open("./scrapers/tabled-committee-reports-2008-2013.html", "r")
		txt = f.read().decode('utf8')
		name_boundary_pairs = []
		startpos = re.search('\<a name', txt).start()
		current_section = ""
		with open('./scrapers/committees.csv', 'r') as csvfile:
			committeesreader = csv.reader(csvfile)
			for row in committeesreader:
				for test in re.finditer('\<a name="' + row[0] + '"', txt):
					if (current_section):
						name_boundary_pairs.append([startpos, test.start(), current_section])
					startpos = test.start()
					current_section = row[1]
		queue = []
		for interval in name_boundary_pairs:
			# print "=== %s ===" % interval[2]
			soup = BeautifulSoup(txt[interval[0]:interval[1]])
			for link in soup.find_all("a", href = True):
				if (link.get_text() != "back to top"):
					url = link['href']
					if not re.match("http://", url):
						url = "http://www.pmg.org/" + url.replace("../../../../../../", "")
					queue.append({ "link": url, "name": link.get_text(), "committee": interval[2].strip()})
		for item in queue:
			if (self._report_exists(item["name"], item["committee"]) == False):
				# print "Processing report %s" % item["name"]
				page = requests.get(item["link"]).text
				self._save_tabledreport(item["name"], item["committee"], page)
		print self.missing_committees

	def members(self):
		list_url = "http://www.pa.org.za/organisation/national-assembly/people/"
		with open('./scrapers/members.csv', 'w') as csvfile:
			memberswriter = csv.writer(csvfile)
			memberswriter.writerow(["url", "name"])
			while True:
				html = requests.get(list_url).content
				soup = BeautifulSoup(html)
				for item in soup.select(".person-list-item a"):
					url = item["href"]
					if "person" in url:
						name = item.select(".name")[0].get_text()
						member = [ url, name.encode("utf-8") ]
						memberswriter.writerow(member);
				next = soup.select("a.next")
				if next:
					list_url = urljoin(list_url, next[0]["href"])
				else:
					break

if (__name__ == "__main__"):
	parser = argparse.ArgumentParser(description='Scrapers for PMG')
	parser.add_argument('scraper')
	args = parser.parse_args()
	scraper = Scraper()
	method = getattr(scraper, args.scraper)
	if not method:
		raise Exception("Method %s not implemented" % args.scraper)
	method()