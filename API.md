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