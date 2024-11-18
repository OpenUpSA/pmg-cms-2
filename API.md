PMG API
=======

The API for the PMG website is freely available at https://api.pmg.org.za. Here we document what's in the API and how to use it.

The API is read-only and doesn't permit updating content.

Authentication
--------------

Most of the content is available for free via the API. If you are a registered user, and you wish to have access to restricted content through the API, then please follow these steps:

1. Login to the website at https://pmg.org.za using your browser.
2. Visit https://api.pmg.org.za/user/ and get the authentication token from the JSON response.
3. Include the authentication token in subsequent requests to tha API in a header named `Authentication-Token`.
4. You can check if you are correctly authenticated by doing a GET against https://api.pmg.org.za/user/

Content Types
-------------

There are many different types of content available:

* Bills `bill`: bills tabled in Parliament
* Briefings `briefing`: speeches and briefings given by ministers
* Calls for comments `call-for-comment`: requests for the public to make comments
* Committee meetings `committee-meeting`: meetings of Parliamentary committees
* Commitee `committee`: Parliamentary commitees
* Daily schedule `daily-schedule`: Parliament's daily schedule of meetings
* Gazette `gazette`: a limited collection of Government gazettes and whitepapers
* Hansard `hansard`: records of the happenings in Parliamentary sessions
* Member `member`: Members of Parliament
* Policy documents `policy-document`: policies and other documents released by parliament
* Questions and replies `question_reply`: questions asked of Ministers and their replies
* Tabled committee reports `tabled-committee-report`: reports tabled by Parliamentary committees

Pagination
----------

PMG has over 17 years of content and most content types are returned in pages, with 50 results per page. A paginated response will have a `next` field with a URL for the next page of results. Pages are numbered from 0.

```json
{
  "count": 117,
  "results": [ ... ],
  "next": "https://api.pmg.org.za/committee/?page=2"
}
```

When you've reached the last page the value of `next` will be `null`.

The total number of records across all pages is given in the `count` field.

Filtering
---------

Content types can be filtered, for example to limit committee meetings to a specific committee.

To filter a content type, provide a `filter[field]=value` query parameter. 

* `field` is the name of a field to filter on
* `value` is the value to match

For example, for committee meetings for the NCOP Economic and Business Development committee which has a `committee_id` of 97, use:

    https://api.pmg.org.za/committee-meeting/?filter[committee_id]=97

Most fields can be used as filters. You cannot filter on nested fields.

Searching
---------

You can search across all API content using the `/search` endpoint.

    https://api.pmg.org.za/search/?q=internet

You can adjust the results with the following parameters:

* `type` - return only certain data types, such as `committee-meeting`, `bill`, etc.
* `page` - the page number in the set of results, use this to paginate through the results
* `per_page` - number of results to return per page
* `start_date` - only find results with a date field on or after this date (ISO8601)
* `end_date` - only find results with a date field on or before this date (ISO8601)
* `committee` - only find results for this particular committee id (INT)

The results deliberately don't return all information for a content type. Use the included `_id` and `_type`
fields to lookup further information using the API.
