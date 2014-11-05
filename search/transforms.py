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
			"title": "name"
		},
		"hansard": {
			"id": "id",
			"title": "title",
			"fulltext": "body"
		}
	}