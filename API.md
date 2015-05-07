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
  "next": "http://api.pmg.org.za/committee/?page=2"
}
```

When you've reached the last page the value of `next` will be `null`.

The total number of records across all pages is given in the `count` field.