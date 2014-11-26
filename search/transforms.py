class Transforms:
	convert_rules = {
		"committee": {
			"id": "id",
			"title": "name",
			"description": ["info", "about"]
		},
		"committee-meeting": {
			"id": "id",
			"title": "title",
			"description": ["content", 0, "summary"],
			"fulltext": ["content", 0, "body"]
		},
		"member": {
			"id": "id",
			"title": "name",
			"description": "bio"
		},
		"bill": {
			"id": "id",
			"title": "title",
			"description": "bill_code"
		},
		"hansard": {
			"id": "id",
			"title": "title",
			"fulltext": "body"
		},
		"briefing": {
			"id": "id",
			"title": "title",
			"description": "summary",
			"fulltext": "minutes"
		},
		"question_reply": {
			"id": "id",
			"title": "title",
			"fulltext": "body"
		},
		"tabled_committee_report": {
			"id": "id",
			"title": "title",
			"fulltext": "body",
			"date": "start_date",
		},
		"calls_for_comment": {
			"id": "id",
			"title": "title",
			"fulltext": "body",
			"date": "start_date",
		}
	}

	data_types = ['committee', 'committee-meeting', 'member', 'bill', 'hansard', 'briefing', 'question_reply', 'tabled_committee_report', 'calls_for_comment']